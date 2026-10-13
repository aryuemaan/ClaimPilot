"""ClaimPilot API + static frontend.

Run locally:  uvicorn app.main:app --reload --port 8080   (from the backend/ folder)
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import random
import uuid
import warnings
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps
from pydantic import BaseModel

from . import genai_utils, storage
from .agents import copilot, pipeline
from .agents.offline import inr
from .config import settings
from .timeutil import now_iso
from .demo import seed as seeder

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("claimpilot")

try:  # iPhone HEIC photos
    from pillow_heif import register_heif_opener

    register_heif_opener()
except Exception:
    pass

RUNNING: set[asyncio.Task] = set()
_seed_lock = asyncio.Lock()


async def _ensure_fresh_demo_data() -> None:
    """Demo stories use dates relative to 'today'. If the data was generated on an earlier day
    (e.g. the service has been running for a while), regenerate it - existing claims are kept."""
    if not settings.auto_seed:
        return
    meta = await storage.docs.get("meta", "seed")
    if meta and meta.get("seeded_on") == date.today().isoformat():
        return
    async with _seed_lock:
        meta = await storage.docs.get("meta", "seed")
        if not meta or meta.get("seeded_on") != date.today().isoformat():
            await seeder.seed(date.today(), wipe_claims=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("ClaimPilot starting - mode=%s backend=%s model=%s store=%s", settings.mode, settings.backend_label,
             settings.gemini_model, storage.describe())
    if settings.auto_seed:
        try:
            await _ensure_fresh_demo_data()
        except Exception:
            log.exception("Seeding failed")
    yield


app = FastAPI(title="ClaimPilot", version=settings.app_version, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _now() -> str:
    return now_iso()


def _spawn(coro) -> None:
    task = asyncio.create_task(coro)
    RUNNING.add(task)
    task.add_done_callback(RUNNING.discard)


# ---------------------------------------------------------------------------
# Health & demo data
# ---------------------------------------------------------------------------


@app.get("/api/health")
async def health():
    meta = await storage.docs.get("meta", "seed")
    return {
        "ok": True,
        "version": settings.app_version,
        "mode": settings.mode,
        "backend": settings.backend_label,
        "model": None if settings.offline else settings.gemini_model,
        "adjudicator_model": None if settings.offline else settings.adjudicator_model,
        "gemma_model": settings.gemma_model if settings.gemma_enabled else None,
        "storage": storage.describe(),
        "seeded_on": (meta or {}).get("seeded_on"),
    }


class ResetBody(BaseModel):
    process_samples: bool = False


@app.post("/api/demo/reset")
async def reset_demo(body: ResetBody):
    result = await seeder.seed(date.today(), wipe_claims=True)
    if body.process_samples:
        _spawn(_process_samples())
    return result


@app.post("/api/demo/process-samples")
async def process_samples():
    _spawn(_process_samples())
    return {"ok": True}


async def _process_samples():
    for key in ("genuine", "partial", "fraud"):
        kit = await storage.docs.get("samples", key)
        if not kit:
            continue
        uploads = []
        for f in kit["files"]:
            loaded = await storage.files.load(f["key"])
            if loaded:
                uploads.append((f["name"], f["kind"], loaded[0], loaded[1]))
        claim_id = await _create_claim(kit["policy_number"], kit["statement"], kit["language"], uploads, channel="sample")
        await pipeline.run_claim(claim_id)


@app.get("/api/demo/samples")
async def list_samples():
    await _ensure_fresh_demo_data()
    kits = await storage.docs.list("samples")
    order = {"genuine": 0, "partial": 1, "fraud": 2}
    kits.sort(key=lambda k: order.get(k["key"], 9))
    return [{k: v for k, v in kit.items() if k != "offline"} for kit in kits]


@app.get("/api/demo/samples/{key}/files/{name}")
async def sample_file(key: str, name: str):
    kit = await storage.docs.get("samples", key)
    f = next((f for f in (kit or {}).get("files", []) if f["name"] == name), None)
    loaded = await storage.files.load(f["key"]) if f else None
    if not loaded:
        raise HTTPException(404, "Sample file not found")
    return Response(loaded[0], media_type=loaded[1], headers={"Cache-Control": "no-store"})


# ---------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------


def _public_policy(p: dict) -> dict:
    v = p.get("vehicle", {})
    return {
        "policy_number": p["policy_number"],
        "holder_name": p["holder_name"],
        "first_name": p["first_name"],
        "phone_masked": p.get("phone_masked"),
        "language": p.get("language", "en"),
        "language_name": p.get("language_name", "English"),
        "vehicle": {k: v.get(k) for k in ("registration", "make_model", "year", "colour", "segment")},
        "start_date": p["start_date"],
        "end_date": p["end_date"],
        "idv": p.get("idv"),
        "addons": p.get("addons", []),
    }


@app.get("/api/policies/lookup")
async def lookup_policy(q: str):
    await _ensure_fresh_demo_data()
    q_norm = "".join(c for c in q.upper() if c.isalnum())
    for p in await storage.docs.list("policies"):
        number = "".join(c for c in p["policy_number"] if c.isalnum())
        phone = "".join(c for c in p.get("phone", "") if c.isdigit())
        reg = "".join(c for c in p["vehicle"]["registration"] if c.isalnum())
        if q_norm and (q_norm == number or q_norm == reg or (len(q_norm) >= 10 and phone.endswith(q_norm[-10:]))):
            return _public_policy(p)
    raise HTTPException(404, "No policy found for that number. Check the policy number, mobile number or vehicle registration.")


@app.get("/api/policies/{number}/document")
async def policy_document(number: str):
    p = await storage.docs.get("policies", number)
    loaded = await storage.files.load(p["pdf_key"]) if p and p.get("pdf_key") else None
    if not loaded:
        raise HTTPException(404, "Policy document not found")
    return Response(loaded[0], media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{number}.pdf"'})


# ---------------------------------------------------------------------------
# Voice
# ---------------------------------------------------------------------------


@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...), language: str = Form("")):
    data = await audio.read()
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(413, "Voice note is too long. Keep it under 2 minutes.")
    mime = (audio.content_type or "audio/wav").split(";")[0]
    if settings.offline:
        return JSONResponse({"offline": True, "message": "Voice transcription needs Gemini. Type your statement, or use the sample statement."},
                            status_code=503)
    try:
        return await genai_utils.transcribe(data, mime, language or None)
    except Exception as exc:
        log.exception("Transcription failed")
        raise HTTPException(502, f"Couldn't transcribe the recording: {str(exc)[:160]}")


# ---------------------------------------------------------------------------
# Claims
# ---------------------------------------------------------------------------


def _normalise_upload(data: bytes, mime: str, kind: str) -> tuple[bytes, str]:
    """Downscale big photos (keeping EXIF) so Gemini requests stay small and fast."""
    if kind != "photo" and not mime.startswith("image/"):
        return data, mime
    try:
        img = Image.open(io.BytesIO(data))
        exif = img.info.get("exif") or img.getexif().tobytes()
        img = ImageOps.exif_transpose(img).convert("RGB")
        if max(img.size) > 2048:
            img.thumbnail((2048, 2048))
        elif mime in ("image/jpeg", "image/jpg"):
            return data, "image/jpeg"
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=88, exif=exif or b"")
        return buf.getvalue(), "image/jpeg"
    except Exception:
        return data, mime


async def _new_claim_id() -> str:
    for _ in range(20):
        cid = f"CLM-{date.today().year}-{random.randint(10000, 99999)}"
        if not await storage.docs.get("claims", cid):
            return cid
    return f"CLM-{uuid.uuid4().hex[:8].upper()}"


async def _create_claim(policy_number: str, statement: str, language: str, uploads: list[tuple[str, str, bytes, str]],
                        channel: str = "app", transcript: dict | None = None) -> str:
    policy = await storage.docs.get("policies", policy_number)
    if not policy:
        raise HTTPException(404, "Unknown policy number")
    claim_id = await _new_claim_id()
    files_meta = []
    index = 0
    # photos first, then documents, then voice - FILE numbers follow this order
    order = {"photo": 0, "document": 1, "voice": 2}
    for name, kind, data, mime in sorted(uploads, key=lambda u: order.get(u[1], 1)):
        kind = kind if kind in order else "document"
        data, mime = _normalise_upload(data, mime, kind) if kind != "voice" else (data, mime)
        fid = uuid.uuid4().hex[:10]
        key = f"claims/{claim_id}/{fid}-{Path(name).name}"
        await storage.files.save(key, data, mime)
        meta = {"id": fid, "name": Path(name).name, "kind": kind, "mime": mime, "key": key, "size": len(data)}
        if kind != "voice":
            index += 1
            meta["index"] = index
        files_meta.append(meta)
    v = policy["vehicle"]
    now = _now()
    claim = {
        "id": claim_id,
        "created_at": now,
        "updated_at": now,
        "reported_on": date.today().isoformat(),
        "status": "queued",
        "channel": channel,
        "policy_number": policy_number,
        "claimant": {"name": policy["holder_name"], "first_name": policy["first_name"], "phone_masked": policy.get("phone_masked"),
                     "language": language or policy.get("language", "en"), "language_name": policy.get("language_name", "English")},
        "vehicle": {"registration": v["registration"], "make_model": v["make_model"], "year": v["year"], "colour": v.get("colour")},
        "statement": statement,
        "transcript": transcript,
        "files": files_meta,
        "trace": [dict(s, status="pending", summary="") for s in pipeline.STEPS],
        "timeline": [{"at": now, "kind": "submitted", "text": "Claim submitted"}],
        "audit": [{"at": now, "actor": "claimant", "action": "submitted", "detail": f"{len(files_meta)} files via {channel}"}],
        "chat": {"adjuster": [], "customer": []},
    }
    await storage.docs.put("claims", claim_id, claim)
    return claim_id


@app.post("/api/claims")
async def create_claim(
    policy_number: str = Form(...),
    statement: str = Form(""),
    language: str = Form(""),
    transcript: str = Form(""),
    kinds: list[str] = Form([]),
    files: list[UploadFile] = File([]),
):
    if not statement.strip() and not files:
        raise HTTPException(400, "Tell us what happened or add at least one photo.")
    if len(files) > 12:
        raise HTTPException(400, "Please upload at most 12 files.")
    uploads = []
    for i, f in enumerate(files):
        data = await f.read()
        if len(data) > 20 * 1024 * 1024:
            raise HTTPException(413, f"{f.filename} is larger than 20 MB.")
        kind = kinds[i] if i < len(kinds) else ("photo" if (f.content_type or "").startswith("image/") else "document")
        uploads.append((f.filename or f"file{i}", kind, data, (f.content_type or "application/octet-stream").split(";")[0]))
    tr = json.loads(transcript) if transcript else None
    claim_id = await _create_claim(policy_number, statement.strip(), language, uploads, channel="app", transcript=tr)
    _spawn(pipeline.run_claim(claim_id))
    return {"claim_id": claim_id}


@app.post("/api/claims/{claim_id}/rerun")
async def rerun(claim_id: str):
    claim = await storage.docs.get("claims", claim_id)
    if not claim:
        raise HTTPException(404, "Claim not found")
    if claim.get("status") == "processing":
        raise HTTPException(409, "Claim is already being analysed")
    _spawn(pipeline.run_claim(claim_id))
    return {"ok": True}


def _list_row(c: dict) -> dict:
    ai = c.get("ai") or {}
    return {
        "id": c["id"],
        "created_at": c["created_at"],
        "updated_at": c.get("updated_at"),
        "status": c["status"],
        "claimant": c["claimant"]["name"],
        "language_name": c["claimant"].get("language_name"),
        "vehicle": c["vehicle"],
        "claimed_amount": (ai.get("estimate") or {}).get("vehicle_claimed_amount") or (ai.get("intake") or {}).get("claimed_amount_inr"),
        "recommended_payout": c.get("recommended_payout"),
        "recommendation": c.get("recommendation"),
        "risk_level": c.get("risk_level"),
        "risk_score": c.get("risk_score"),
        "fast_track": c.get("fast_track"),
        "processing_seconds": c.get("processing_seconds"),
        "final_decision": c.get("final_decision"),
        "incident_type": (ai.get("intake") or {}).get("incident_type"),
        "headline": (ai.get("decision") or {}).get("headline"),
    }


@app.get("/api/claims")
async def list_claims():
    claims = await storage.docs.list("claims")
    claims.sort(key=lambda c: c["created_at"], reverse=True)
    return [_list_row(c) for c in claims]


def _adjuster_view(c: dict) -> dict:
    out = {k: v for k, v in c.items() if k not in ("statement_raw",)}
    for f in out.get("files", []):
        f["url"] = f"/api/claims/{c['id']}/files/{f['id']}"
    return out


def _customer_view(c: dict) -> dict:
    ai = c.get("ai") or {}
    dec = ai.get("decision") or {}
    est = ai.get("estimate") or {}
    cov = ai.get("coverage") or {}
    groups: dict[str, list[str]] = {}
    for s in c.get("trace", []):
        groups.setdefault(s.get("customer_label") or s.get("label"), []).append(s["status"])
    progress = []
    for label, statuses in groups.items():
        if "error" in statuses:
            st = "error"
        elif all(x == "done" for x in statuses):
            st = "done"
        elif "running" in statuses or "done" in statuses:
            st = "running"
        else:
            st = "pending"
        progress.append({"label": label, "status": st})
    view = {
        "id": c["id"],
        "status": c["status"],
        "created_at": c["created_at"],
        "updated_at": c.get("updated_at"),
        "claimant": c["claimant"],
        "vehicle": c["vehicle"],
        "progress": progress,
        "timeline": c.get("timeline", []),
        "error": c.get("error"),
        "files": [{"id": f["id"], "name": f["name"], "kind": f["kind"], "url": f"/api/claims/{c['id']}/files/{f['id']}"}
                  for f in c.get("files", []) if f["kind"] != "voice"],
        "final_decision": c.get("final_decision"),
        "chat": (c.get("chat") or {}).get("customer", []),
    }
    if ai:
        view["summary"] = {
            "message_local": dec.get("customer_message_local"),
            "message_english": dec.get("customer_message_english"),
            "language": dec.get("customer_language"),
            "estimated_payout": dec.get("recommended_payout_inr") if dec.get("recommendation") in ("approve", "approve_partial") else None,
            "estimate": {k: est.get(k) for k in ("gross_total", "depreciation_total", "deductible", "recommended_payout", "zero_dep")}
            if dec.get("recommendation") in ("approve", "approve_partial") else None,
            "coverage": [{k: i.get(k) for k in ("item", "status", "reason", "clause_ref")} for i in cov.get("items", [])]
            if dec.get("recommendation") in ("approve", "approve_partial") else [],
            "damaged_parts": [{"part_name": p.get("part_name"), "action": p.get("action")} for p in (ai.get("damage") or {}).get("damaged_parts", [])],
        }
    return view


@app.get("/api/claims/{claim_id}")
async def get_claim(claim_id: str):
    c = await storage.docs.get("claims", claim_id)
    if not c:
        raise HTTPException(404, "Claim not found")
    return _adjuster_view(c)


@app.get("/api/claims/{claim_id}/public")
async def get_claim_public(claim_id: str):
    c = await storage.docs.get("claims", claim_id.strip().upper())
    if not c:
        raise HTTPException(404, "We couldn't find that claim number.")
    return _customer_view(c)


@app.get("/api/claims/{claim_id}/stream")
async def stream_claim(claim_id: str, request: Request, audience: str = "adjuster"):
    view = _customer_view if audience == "customer" else _adjuster_view

    async def gen():
        last = None
        idle = 0
        for _ in range(1800):  # ~25 minutes max
            if await request.is_disconnected():
                break
            c = await storage.docs.get("claims", claim_id)
            if not c:
                yield "event: error\ndata: {\"error\": \"not found\"}\n\n"
                break
            stamp = c.get("updated_at")
            if stamp != last:
                last = stamp
                idle = 0
                yield f"data: {json.dumps(view(c), ensure_ascii=False, default=str)}\n\n"
            else:
                idle += 1
                if idle % 20 == 0:
                    yield ": keep-alive\n\n"
            await asyncio.sleep(0.8)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/claims/{claim_id}/files/{file_id}")
async def claim_file(claim_id: str, file_id: str):
    c = await storage.docs.get("claims", claim_id)
    f = next((f for f in (c or {}).get("files", []) if f["id"] == file_id), None)
    loaded = await storage.files.load(f["key"]) if f else None
    if not loaded:
        raise HTTPException(404, "File not found")
    return Response(loaded[0], media_type=loaded[1], headers={"Cache-Control": "private, max-age=3600"})


@app.get("/api/past-claims/{claim_id}/photos/{photo_id}")
async def past_claim_photo(claim_id: str, photo_id: str):
    loaded = await storage.files.load(f"past_claims/{claim_id}/{photo_id}")
    if not loaded:
        raise HTTPException(404, "Photo not found")
    return Response(loaded[0], media_type=loaded[1])


class DecisionBody(BaseModel):
    action: str  # approve | approve_partial | request_info | investigate | reject
    amount: float = 0
    note: str = ""
    adjuster: str = "Claims officer"


ACTION_STATUS = {"approve": "approved", "approve_partial": "approved", "reject": "rejected", "request_info": "info_requested",
                 "investigate": "investigating"}


@app.post("/api/claims/{claim_id}/decision")
async def decide(claim_id: str, body: DecisionBody):
    c = await storage.docs.get("claims", claim_id)
    if not c:
        raise HTTPException(404, "Claim not found")
    if body.action not in ACTION_STATUS:
        raise HTTPException(400, "Unknown action")
    if c.get("status") == "processing":
        raise HTTPException(409, "Wait for the AI review to finish")
    ai = c.get("ai") or {}
    dec = ai.get("decision") or {}
    ai_rec = dec.get("recommendation")
    ai_amount = float(dec.get("recommended_payout_inr") or 0)
    same_family = {body.action, ai_rec} <= {"approve", "approve_partial"} or body.action == ai_rec
    amount_changed = body.action.startswith("approve") and abs(body.amount - ai_amount) > max(1, ai_amount * 0.01)
    override = not same_family or amount_changed
    if override and len(body.note.strip()) < 5:
        raise HTTPException(400, "You're overriding the AI recommendation - add a short reason for the audit trail.")
    if body.action in ("request_info", "reject") and len(body.note.strip()) < 5:
        raise HTTPException(400, "Add a note the customer will see.")
    now = _now()
    amount = body.amount if body.action.startswith("approve") else 0
    final = {"action": body.action, "amount": amount, "note": body.note.strip(), "by": body.adjuster, "at": now,
             "override": override, "ai_recommendation": ai_rec, "ai_amount": ai_amount,
             "minutes_to_decide": round((datetime.fromisoformat(now) - datetime.fromisoformat(c.get("processing_finished_at") or c["created_at"])).total_seconds() / 60, 1)}
    audit = c.get("audit", []) + [{"at": now, "actor": body.adjuster, "action": body.action,
                                   "detail": f"{inr(amount)}" + (f" · override of AI '{ai_rec}' ({inr(ai_amount)})" if override else " · agreed with AI")
                                   + (f" · note: {body.note.strip()}" if body.note.strip() else "")}]
    await storage.docs.update("claims", claim_id, {"status": ACTION_STATUS[body.action], "final_decision": final, "audit": audit, "updated_at": now})
    _spawn(_notify_customer(claim_id, final))
    return {"ok": True, "status": ACTION_STATUS[body.action]}


async def _notify_customer(claim_id: str, final: dict) -> None:
    c = await storage.docs.get("claims", claim_id)
    if not c:
        return
    bills = ((c.get("ai") or {}).get("intake") or {}).get("bills") or []
    workshop = next((b.get("vendor") for b in bills if b.get("for_vehicle")), None)
    msg = await genai_utils.customer_update(
        action=final["action"], amount=inr(final["amount"]), note=final.get("note", ""),
        first_name=c["claimant"]["first_name"], claim_id=claim_id,
        language_name=c["claimant"].get("language_name", "English"), workshop=workshop,
    )
    final = dict(final, customer_message=msg)
    timeline = c.get("timeline", []) + [{"at": _now(), "kind": final["action"], "text": msg["local"], "text_english": msg["english"]}]
    await storage.docs.update("claims", claim_id, {"final_decision": final, "timeline": timeline, "updated_at": _now()})


class AskBody(BaseModel):
    question: str
    audience: str = "adjuster"


@app.post("/api/claims/{claim_id}/ask")
async def ask(claim_id: str, body: AskBody):
    c = await storage.docs.get("claims", claim_id)
    if not c:
        raise HTTPException(404, "Claim not found")
    if not c.get("ai"):
        raise HTTPException(409, "The AI review is still running - ask again in a moment.")
    q = body.question.strip()[:800]
    if not q:
        raise HTTPException(400, "Ask a question")
    policy = await storage.docs.get("policies", c["policy_number"]) or {}
    try:
        answer = await copilot.ask(c, policy, q, body.audience)
    except Exception as exc:
        log.exception("Copilot failed")
        raise HTTPException(502, f"ClaimPilot couldn't answer right now: {str(exc)[:160]}")
    audience = "customer" if body.audience == "customer" else "adjuster"
    chat = c.get("chat") or {"adjuster": [], "customer": []}
    chat.setdefault(audience, [])
    now = _now()
    chat[audience] += [{"role": "user", "text": q, "at": now}, {"role": "assistant", "text": answer, "at": now}]
    await storage.docs.update("claims", claim_id, {"chat": chat})
    return {"answer": answer}


# ---------------------------------------------------------------------------
# Insights
# ---------------------------------------------------------------------------


@app.get("/api/insights")
async def insights():
    claims = await storage.docs.list("claims")
    past = await storage.docs.list("past_claims")
    analysed = [c for c in claims if c.get("ai")]
    decided = [c for c in analysed if c.get("final_decision")]
    secs = [c["processing_seconds"] for c in analysed if c.get("processing_seconds")]
    mins = [c["final_decision"].get("minutes_to_decide") for c in decided if c["final_decision"].get("minutes_to_decide") is not None]
    agree = [not c["final_decision"].get("override") for c in decided]
    risk = {"low": 0, "medium": 0, "high": 0}
    recs: dict[str, int] = {}
    held = 0.0
    paid = 0.0
    for c in analysed:
        risk[c.get("risk_level") or "low"] = risk.get(c.get("risk_level") or "low", 0) + 1
        recs[c.get("recommendation") or "-"] = recs.get(c.get("recommendation") or "-", 0) + 1
        est = (c["ai"].get("estimate") or {})
        if c.get("risk_level") == "high":
            held += float(est.get("vehicle_claimed_amount") or 0)
        fd = c.get("final_decision") or {}
        if fd.get("action", "").startswith("approve"):
            paid += float(fd.get("amount") or 0)
    settled = [p for p in past if p.get("days_to_settle")]
    baseline_days = round(sum(p["days_to_settle"] for p in settled) / len(settled), 1) if settled else None
    return {
        "claims_total": len(claims),
        "analysed": len(analysed),
        "awaiting_decision": sum(1 for c in analysed if not c.get("final_decision")),
        "decided": len(decided),
        "avg_ai_seconds": round(sum(secs) / len(secs), 1) if secs else None,
        "avg_minutes_to_decide": round(sum(mins) / len(mins), 1) if mins else None,
        "agreement_rate": round(sum(agree) / len(agree) * 100) if agree else None,
        "fast_track": sum(1 for c in analysed if c.get("fast_track")),
        "risk": risk,
        "recommendations": recs,
        "amount_held_inr": held,
        "amount_approved_inr": paid,
        "baseline": {"avg_days_to_settle": baseline_days, "past_claims": len(past), "source": "Seeded demo history (pre-ClaimPilot)"},
    }


# ---------------------------------------------------------------------------
# Frontend (built React app)
# ---------------------------------------------------------------------------

_dist = settings.frontend_dist
if (_dist / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404)
        candidate = (_dist / path).resolve()
        if path and candidate.is_file() and _dist in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(_dist / "index.html", headers={"Cache-Control": "no-cache"})
else:
    @app.get("/", include_in_schema=False)
    async def no_frontend():
        return JSONResponse({"message": "ClaimPilot API is running. Build the frontend (cd frontend && npm run build) to serve the UI here.",
                             "docs": "/docs"})
