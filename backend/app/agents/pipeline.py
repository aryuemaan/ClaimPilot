"""The ClaimPilot multi-agent pipeline, built with Google ADK.

    claimpilot (SequentialAgent)
    ├── privacy_guard        custom agent · rules + Gemma redaction
    ├── intake_agent         Gemini · reads voice transcript, photos, bills
    ├── specialists (ParallelAgent)
    │   ├── coverage_agent   Gemini · reads the policy wording PDF, cites clauses
    │   ├── damage_agent     Gemini vision · parts, severity, bounding boxes
    │   └── fraud_team (SequentialAgent)
    │       ├── fraud_signals   custom agent · photo hashes, EXIF, bill maths, timing, history
    │       └── fraud_analyst   Gemini · document forensics + risk score
    ├── cost_estimator       custom agent · deterministic parts/labour/depreciation maths
    └── adjudicator          Gemini · decision brief + customer message in their language

Every LLM agent uses an output_schema, so results are structured and validated.
A before_model_callback gives each agent only the files it needs.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import date, datetime, timezone
from typing import AsyncGenerator

from google.adk.agents import BaseAgent, LlmAgent, ParallelAgent, SequentialAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .. import fraud_checks, pricing, privacy, storage
from ..config import settings
from ..timeutil import now_iso
from ..models import CoverageResult, DamageResult, DecisionBrief, FraudResult, IntakeResult
from . import offline, prompts

log = logging.getLogger("claimpilot.pipeline")

APP_NAME = "claimpilot"

# Display metadata for the agent trace (order matters for the UI).
STEPS = [
    {"id": "privacy_guard", "label": "Privacy guard", "customer_label": "Protecting your personal details", "engine": "Rules + Gemma"},
    {"id": "intake_agent", "label": "Intake agent", "customer_label": "Reading your story, photos and bills", "engine": "Gemini"},
    {"id": "coverage_agent", "label": "Coverage agent", "customer_label": "Checking your policy", "engine": "Gemini"},
    {"id": "damage_agent", "label": "Damage agent", "customer_label": "Inspecting the damage", "engine": "Gemini vision"},
    {"id": "fraud_signals", "label": "Fraud signals", "customer_label": "Running routine checks", "engine": "Deterministic tools"},
    {"id": "fraud_analyst", "label": "Fraud analyst", "customer_label": "Running routine checks", "engine": "Gemini"},
    {"id": "cost_estimator", "label": "Cost estimator", "customer_label": "Calculating your estimate", "engine": "Deterministic"},
    {"id": "adjudicator", "label": "Adjudicator", "customer_label": "Preparing your claim summary", "engine": "Gemini"},
]
OUTPUT_TO_STEP = {
    "privacy": "privacy_guard", "intake": "intake_agent", "coverage": "coverage_agent", "damage": "damage_agent",
    "fraud_signals": "fraud_signals", "fraud": "fraud_analyst", "estimate": "cost_estimator", "decision": "adjudicator",
}

# claim_id -> per-run binary attachments (policy PDF) for callbacks
RUN_FILES: dict[str, dict] = {}
# claim_id -> Tracker
TRACKERS: dict[str, "Tracker"] = {}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


def make_model(which: str = "default"):
    if settings.offline:
        return offline.OfflineDemoLlm()
    from google.adk.models import Gemini

    name = settings.adjudicator_model if which == "adjudicator" else settings.gemini_model
    return Gemini(
        model=name,
        retry_options=types.HttpRetryOptions(attempts=4, initial_delay=2.0, max_delay=20.0,
                                             http_status_codes=[408, 429, 500, 502, 503, 504]),
    )


def gen_config() -> types.GenerateContentConfig | None:
    if settings.offline or not settings.thinking_level:
        return None
    return types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level=settings.thinking_level.upper())
    )


# ---------------------------------------------------------------------------
# Progress tracking (drives the live UI)
# ---------------------------------------------------------------------------


class Tracker:
    def __init__(self, claim_id: str) -> None:
        self.claim_id = claim_id
        self.trace = [dict(s, status="pending", started_at=None, ended_at=None, ms=None, summary="") for s in STEPS]
        self._lock = asyncio.Lock()
        self._t0: dict[str, float] = {}

    def _step(self, sid: str) -> dict | None:
        return next((s for s in self.trace if s["id"] == sid), None)

    async def _save(self) -> None:
        await storage.docs.update("claims", self.claim_id, {"trace": self.trace, "updated_at": now_iso()})

    async def start(self, sid: str) -> None:
        async with self._lock:
            s = self._step(sid)
            if s and s["status"] == "pending":
                s["status"] = "running"
                s["started_at"] = now_iso()
                self._t0[sid] = time.perf_counter()
                await self._save()

    async def done(self, sid: str, summary: str) -> None:
        async with self._lock:
            s = self._step(sid)
            if s and s["status"] != "done":
                s["status"] = "done"
                s["ended_at"] = now_iso()
                s["ms"] = int((time.perf_counter() - self._t0.get(sid, time.perf_counter())) * 1000)
                s["summary"] = summary
                await self._save()

    async def fail(self, message: str) -> None:
        async with self._lock:
            for s in self.trace:
                if s["status"] == "running":
                    s["status"] = "error"
                    s["summary"] = message[:200]
            await self._save()


def _start_cb(step_id: str):
    async def cb(callback_context):
        tr = TRACKERS.get(callback_context.state.get("claim_id"))
        if tr:
            await tr.start(step_id)
        return None
    return cb


def summarize(key: str, v: dict) -> str:
    try:
        if key == "privacy":
            n = len(v.get("findings", []))
            return f"Masked {n} identifier{'s' if n != 1 else ''} · Gemma {v.get('gemma_status')}"
        if key == "intake":
            return f"{v.get('language')} · {v.get('incident_type')} on {v.get('incident_date')} · {len(v.get('documents', []))} files read"
        if key == "coverage":
            return f"{v.get('verdict', '').replace('_', ' ').capitalize()} · {len(v.get('items', []))} items checked"
        if key == "damage":
            ok = "consistent with story" if v.get("consistent_with_statement") else "does NOT match story"
            return f"{len(v.get('damaged_parts', []))} damaged parts · {v.get('impact_direction')} impact · {ok}"
        if key == "fraud_signals":
            return f"{v.get('checked')} checks · {v.get('flags')} flagged"
        if key == "fraud":
            return f"Risk {v.get('risk_score')}/100 ({v.get('risk_level')})"
        if key == "estimate":
            return f"Payable {offline.inr(v.get('recommended_payout', 0))} of {offline.inr(v.get('gross_total', 0))} repair cost"
        if key == "decision":
            return f"{v.get('recommendation', '').replace('_', ' ')} · {v.get('confidence')}% confidence"
    except Exception:
        pass
    return "Done"


# ---------------------------------------------------------------------------
# File routing: each agent only sees what it needs
# ---------------------------------------------------------------------------

_LABEL = re.compile(r"\[\[FILE \d+ \| kind=(\w+)")


def file_router(include_kinds: set[str], attach_policy: bool = False):
    async def cb(callback_context, llm_request):
        contents = llm_request.contents or []
        if not contents:
            return None
        parts: list[types.Part] = []
        keep = True
        for p in contents[0].parts or []:
            if p.text and p.text.startswith("[[FILE"):
                m = _LABEL.match(p.text)
                keep = bool(m and m.group(1) in include_kinds)
                if keep:
                    parts.append(p)
                continue
            if p.inline_data is not None or p.file_data is not None:
                if keep:
                    parts.append(p)
                continue
            parts.append(p)
        if attach_policy:
            run = RUN_FILES.get(callback_context.state.get("claim_id"), {})
            pdf = run.get("policy_pdf")
            if pdf:
                parts.append(types.Part.from_text(text="[[POLICY WORDING PDF]]"))
                parts.append(types.Part.from_bytes(data=pdf, mime_type="application/pdf"))
        # Other agents' outputs reach this agent through its instruction (session state), so
        # the earlier "for context" turns are dropped to keep requests small and fast.
        llm_request.contents = [types.Content(role="user", parts=parts)]
        return None
    return cb


# ---------------------------------------------------------------------------
# Deterministic agents
# ---------------------------------------------------------------------------


class PrivacyGuardAgent(BaseAgent):
    """Masks Aadhaar/PAN/phone/email/card/bank numbers, then asks Gemma for anything the rules missed."""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        raw = ctx.session.state.get("raw_statement", "")
        result = await privacy.redact(raw)
        yield Event(author=self.name, invocation_id=ctx.invocation_id,
                    actions=EventActions(state_delta={"privacy": result, "masked_statement": result["masked_text"]}))


class FraudSignalsAgent(BaseAgent):
    """Runs the deterministic fraud tools and hands hard evidence to the analyst."""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        st = ctx.session.state
        result = fraud_checks.run_all_checks(
            photo_hashes=st.get("photo_hashes", []),
            photo_meta=st.get("photo_meta", []),
            history=st.get("history", []),
            policy=st.get("policy", {}),
            intake=st.get("intake", {}) or {},
            claimant_claims_12m=int(st.get("claims_last_12m", 0)),
            reported_on=date.fromisoformat(st.get("reported_on")),
        )
        yield Event(author=self.name, invocation_id=ctx.invocation_id, actions=EventActions(state_delta={"fraud_signals": result}))


class CostEstimatorAgent(BaseAgent):
    """Turns the damaged-parts list into rupees: parts, labour, paint, GST, depreciation, deductible."""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        st = ctx.session.state
        policy = st.get("policy", {})
        v = policy.get("vehicle", {})
        intake = st.get("intake", {}) or {}
        damage = st.get("damage", {}) or {}
        coverage = st.get("coverage", {}) or {}
        incident = fraud_checks._parse_date(intake.get("incident_date")) or date.fromisoformat(st.get("reported_on"))
        reg = date.fromisoformat(v.get("registration_date", f"{v.get('year', incident.year)}-01-01"))
        bills = intake.get("bills") or []
        vehicle_bills = [b for b in bills if b.get("for_vehicle", True)]
        claimed = sum(float(b.get("total") or 0) for b in vehicle_bills) if vehicle_bills else float(intake.get("claimed_amount_inr") or 0)
        est = pricing.estimate_claim(
            damage.get("damaged_parts", []),
            segment=v.get("segment", "hatchback"),
            vehicle_age_months=pricing.months_between(reg, incident),
            zero_dep="Zero Depreciation" in (policy.get("addons") or []),
            deductible=pricing.compulsory_deductible(int(v.get("cc", 1200))),
            claimed_amount=claimed,
        )
        start = fraud_checks._parse_date(policy.get("start_date"))
        end = fraud_checks._parse_date(policy.get("end_date"))
        in_period = bool(start and end and start <= incident <= end)
        if not in_period or coverage.get("verdict") == "not_covered":
            est["recommended_payout"] = 0
            est["not_payable_reason"] = "Incident outside the period of insurance" if not in_period else "Not covered under the policy"
        est["incident_in_policy_period"] = in_period
        est["vehicle_claimed_amount"] = claimed
        yield Event(author=self.name, invocation_id=ctx.invocation_id, actions=EventActions(state_delta={"estimate": est}))


# ---------------------------------------------------------------------------
# Agent tree
# ---------------------------------------------------------------------------


def _instr(fn):
    return lambda ctx: fn(dict(ctx.state))


def build_pipeline() -> SequentialAgent:
    flash = make_model()
    judge = make_model("adjudicator")
    cfg = gen_config()

    def llm(name, prompt, schema, key, model, router):
        return LlmAgent(
            name=name,
            description=f"ClaimPilot {name.replace('_', ' ')}",
            model=model,
            instruction=_instr(prompt),
            output_schema=schema,
            output_key=key,
            generate_content_config=cfg,
            before_model_callback=router,
            before_agent_callback=_start_cb(name),
            disallow_transfer_to_parent=True,
            disallow_transfer_to_peers=True,
        )

    privacy_guard = PrivacyGuardAgent(name="privacy_guard", description="Redacts personal identifiers",
                                      before_agent_callback=_start_cb("privacy_guard"))
    intake = llm("intake_agent", prompts.intake, IntakeResult, "intake", flash, file_router({"photo", "document"}))
    coverage = llm("coverage_agent", prompts.coverage, CoverageResult, "coverage", flash, file_router(set(), attach_policy=True))
    damage = llm("damage_agent", prompts.damage, DamageResult, "damage", flash, file_router({"photo"}))
    signals = FraudSignalsAgent(name="fraud_signals", description="Deterministic fraud checks",
                                before_agent_callback=_start_cb("fraud_signals"))
    analyst = llm("fraud_analyst", prompts.fraud, FraudResult, "fraud", flash, file_router({"document"}))
    estimator = CostEstimatorAgent(name="cost_estimator", description="Repair cost and payout maths",
                                   before_agent_callback=_start_cb("cost_estimator"))
    adjudicator = llm("adjudicator", prompts.adjudicator, DecisionBrief, "decision", judge, file_router(set()))

    return SequentialAgent(
        name="claimpilot",
        description="End-to-end motor claim triage",
        sub_agents=[
            privacy_guard,
            intake,
            ParallelAgent(name="specialists", sub_agents=[
                coverage,
                damage,
                SequentialAgent(name="fraud_team", sub_agents=[signals, analyst]),
            ]),
            estimator,
            adjudicator,
        ],
    )


_session_service = InMemorySessionService()
_runner: Runner | None = None


def runner() -> Runner:
    global _runner
    if _runner is None:
        _runner = Runner(app_name=APP_NAME, agent=build_pipeline(), session_service=_session_service)
    return _runner


# ---------------------------------------------------------------------------
# Running a claim
# ---------------------------------------------------------------------------


def _photo_forensics(data: bytes, name: str, file_id: str) -> tuple[dict | None, dict | None]:
    try:
        hashes = fraud_checks.multi_hash(data)
    except Exception:
        return None, None
    taken = fraud_checks.exif_datetime(data)
    return ({"file_id": file_id, "name": name, "hashes": hashes},
            {"file_id": file_id, "name": name, "taken_at": taken.isoformat() if taken else None})


async def run_claim(claim_id: str) -> None:
    docs, files = storage.docs, storage.files
    claim = await docs.get("claims", claim_id)
    if not claim:
        return
    tracker = Tracker(claim_id)
    TRACKERS[claim_id] = tracker
    t0 = time.perf_counter()
    started = datetime.now(timezone.utc)
    await docs.update("claims", claim_id, {"status": "processing", "trace": tracker.trace, "error": None,
                                           "processing_started_at": started.isoformat(), "updated_at": started.isoformat()})
    try:
        policy = await docs.get("policies", claim["policy_number"]) or {}
        history = [h for h in await docs.list("past_claims")]
        policy_for_state = {k: v for k, v in policy.items() if k not in ("wording_text",)}

        header = (f"NEW MOTOR CLAIM {claim_id}. Policy: {claim['policy_number']}. Reported on {claim['reported_on']}. "
                  f"Files follow, each introduced by a [[FILE n | kind | name]] label.")
        parts = [types.Part.from_text(text=header)]
        photo_hashes, photo_meta = [], []
        for f in claim["files"]:
            if not f.get("index"):
                continue  # voice notes are represented by their transcript
            loaded = await files.load(f["key"])
            if not loaded:
                continue
            data, mime = loaded
            if f["kind"] == "photo":
                h, m = _photo_forensics(data, f["name"], f["id"])
                if h:
                    photo_hashes.append(h)
                    photo_meta.append(m)
            parts.append(types.Part.from_text(text=f"[[FILE {f['index']} | kind={f['kind']} | name={f['name']}]]"))
            parts.append(types.Part.from_bytes(data=data, mime_type=mime))

        pdf = await files.load(policy["pdf_key"]) if policy.get("pdf_key") else None
        RUN_FILES[claim_id] = {"policy_pdf": pdf[0] if pdf else None}

        if settings.offline and policy.get("scenario"):
            sample = await docs.get("samples", policy["scenario"])
            if sample:
                offline.SCRIPTS[claim_id] = sample.get("offline", {})

        state = {
            "claim_id": claim_id,
            "today": date.today().isoformat(),
            "reported_on": claim["reported_on"],
            "raw_statement": claim.get("statement", ""),
            "policy": policy_for_state,
            "history": [{"id": h["id"], "claimant_masked": h.get("claimant_masked"), "vehicle": h.get("vehicle"),
                         "incident_date": h.get("incident_date"), "photos": h.get("photos", [])} for h in history],
            "claims_last_12m": policy.get("claims_last_12m", 0),
            "photo_hashes": photo_hashes,
            "photo_meta": photo_meta,
        }
        session = await _session_service.create_session(app_name=APP_NAME, user_id=claim_id, state=state)
        msg = types.Content(role="user", parts=parts)

        async def consume():
            async for event in runner().run_async(user_id=claim_id, session_id=session.id, new_message=msg):
                if event.error_message:
                    raise RuntimeError(f"{event.author}: {event.error_code} {event.error_message}")
                for key, value in (event.actions.state_delta or {}).items():
                    step = OUTPUT_TO_STEP.get(key)
                    if step and isinstance(value, dict):
                        await tracker.done(step, summarize(key, value))

        try:
            await asyncio.wait_for(consume(), timeout=settings.pipeline_timeout)
        except asyncio.TimeoutError:
            raise RuntimeError(f"The agents took longer than {settings.pipeline_timeout} s. Press Retry.")

        final = await _session_service.get_session(app_name=APP_NAME, user_id=claim_id, session_id=session.id)
        st = final.state
        ai = {k: st.get(k) for k in ("privacy", "intake", "coverage", "damage", "fraud_signals", "fraud", "estimate", "decision")}
        missing = [k for k, v in ai.items() if not v]
        if missing:
            raise RuntimeError(f"Agents returned no output for: {', '.join(missing)}")
        ai["photo_meta"] = photo_meta
        _apply_guards(ai)
        seconds = round(time.perf_counter() - t0, 1)
        dec = ai["decision"]
        timeline = claim.get("timeline", []) + [{
            "at": now_iso(),
            "kind": "ai_done",
            "text": "AI review complete - waiting for a claims officer to confirm",
        }]
        await docs.update("claims", claim_id, {
            "status": "review",
            "ai": ai,
            "model": {"engine": settings.backend_label, "model": "offline-demo-model" if settings.offline else settings.gemini_model,
                      "adjudicator": settings.adjudicator_model if not settings.offline else "offline-demo-model",
                      "gemma": settings.gemma_model if settings.gemma_enabled else None, "adk": "google-adk"},
            "processing_seconds": seconds,
            "processing_finished_at": now_iso(),
            "risk_level": ai["fraud"].get("risk_level"),
            "risk_score": ai["fraud"].get("risk_score"),
            "recommendation": dec.get("recommendation"),
            "recommended_payout": dec.get("recommended_payout_inr"),
            "fast_track": dec.get("fast_track_eligible"),
            "timeline": timeline,
            "trace": tracker.trace,
            "updated_at": now_iso(),
        })
        log.info("Claim %s processed in %ss -> %s", claim_id, seconds, dec.get("recommendation"))
    except Exception as exc:  # surface any failure to the UI with a retry option
        log.exception("Pipeline failed for %s", claim_id)
        await tracker.fail(str(exc))
        await docs.update("claims", claim_id, {"status": "error", "error": _friendly_error(exc), "updated_at": now_iso()})
    finally:
        TRACKERS.pop(claim_id, None)
        RUN_FILES.pop(claim_id, None)
        offline.SCRIPTS.pop(claim_id, None)


def _apply_guards(ai: dict) -> None:
    """Business rules that must hold no matter what the model says."""
    dec, est, fr = ai["decision"], ai["estimate"], ai["fraud"]
    rec = dec.get("recommendation")
    if rec in ("approve", "approve_partial"):
        dec["recommended_payout_inr"] = est.get("recommended_payout", 0)
    else:
        dec["recommended_payout_inr"] = 0
    dec["fast_track_eligible"] = bool(
        rec in ("approve", "approve_partial") and fr.get("risk_level") == "low"
        and dec["recommended_payout_inr"] < 50000 and dec.get("confidence", 0) >= 85
    )
    if fr.get("risk_level") == "high" and rec in ("approve", "approve_partial"):
        dec["recommendation"] = "investigate"
        dec["recommended_payout_inr"] = 0
        dec["fast_track_eligible"] = False
        dec.setdefault("rationale", []).append(
            {"point": "Guardrail: high fraud risk always routes to investigation.", "source": "fraud", "impact": "against"})


def _friendly_error(exc: Exception) -> str:
    s = str(exc)
    if "API key" in s or "API_KEY" in s or "PERMISSION_DENIED" in s or "401" in s or "403" in s:
        return "Gemini rejected the credentials. Check GOOGLE_API_KEY (or Vertex AI permissions) and try again."
    if "NOT_FOUND" in s or "404" in s:
        return f"Model not available to this project. Set GEMINI_MODEL to a model you can access (currently {settings.gemini_model})."
    if "RESOURCE_EXHAUSTED" in s or "429" in s:
        return "Gemini rate limit reached. Wait a minute and press Retry."
    return f"The analysis stopped: {s[:240]}"
