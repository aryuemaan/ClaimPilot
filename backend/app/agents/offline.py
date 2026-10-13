"""A scripted stand-in for Gemini, used only when no credentials are configured.

It lets the whole ADK pipeline, both UIs and the demo flow run on any laptop
with no API key. Every response is clearly marked as coming from the offline
model in the UI. With GOOGLE_API_KEY (or Vertex AI) set, this is never used.
"""

from __future__ import annotations

import asyncio
import json
import random
import re
from typing import AsyncGenerator

from google.genai import types
from google.adk.models._capabilities import LlmCapabilities
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse

# claim_id -> scripted answers for that claim (set by the pipeline runner)
SCRIPTS: dict[str, dict] = {}

_ROLE_TO_KEY = {
    "intake_agent": "intake",
    "coverage_agent": "coverage",
    "damage_agent": "damage",
    "fraud_analyst": "fraud",
    "adjudicator": "decision",
}

# Simulated thinking time so the live progress UI behaves like the real thing.
_LATENCY = {"intake": (2.2, 3.4), "coverage": (2.0, 3.0), "damage": (2.6, 3.8), "fraud": (1.8, 2.8), "decision": (2.0, 3.0)}


def inr(amount: float) -> str:
    n = int(round(amount))
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups) + "," + tail
    return ("-" if n < 0 else "") + "₹" + s


def _system_text(req) -> str:
    si = req.config.system_instruction if req.config else None
    if si is None:
        return ""
    if isinstance(si, str):
        return si
    if isinstance(si, types.Content):
        return "".join(p.text or "" for p in si.parts or [])
    return str(si)


def _json_after(label: str, text: str) -> dict:
    """Pull the JSON object that follows 'label' in the instruction."""
    i = text.find(label)
    if i < 0:
        return {}
    start = text.find("{", i)
    if start < 0:
        return {}
    depth = 0
    for j in range(start, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start: j + 1])
                except json.JSONDecodeError:
                    return {}
    return {}


class OfflineDemoLlm(BaseLlm):
    model: str = "offline-demo-model"
    fast: bool = False

    @property
    def capabilities(self) -> LlmCapabilities:
        return LlmCapabilities(output_schema_and_tools=False)

    @classmethod
    def supported_models(cls) -> list[str]:
        return [r"offline-demo-model"]

    async def generate_content_async(self, llm_request, stream: bool = False) -> AsyncGenerator[LlmResponse, None]:
        sys_text = _system_text(llm_request)
        role = re.search(r"ROLE:\s*(\S+)", sys_text)
        role = role.group(1) if role else ""
        claim = re.search(r"Claim ID:\s*(\S+)", sys_text)
        claim_id = claim.group(1) if claim else ""
        key = _ROLE_TO_KEY.get(role)

        if key and not self.fast:
            await asyncio.sleep(random.uniform(*_LATENCY[key]))

        if role.startswith("copilot"):
            text = self._copilot(sys_text, llm_request)
        else:
            script = SCRIPTS.get(claim_id, {})
            payload = script.get(key) if key else None
            payload = json.loads(json.dumps(payload)) if payload else self._generic(key, sys_text, llm_request)
            if key == "decision":
                payload = self._fill_decision(payload, sys_text)
            text = json.dumps(payload, ensure_ascii=False)

        yield LlmResponse(content=types.Content(role="model", parts=[types.Part.from_text(text=text)]))

    # ------------------------------------------------------------------
    def _fill_decision(self, d: dict, sys_text: str) -> dict:
        est = _json_after("Deterministic estimate", sys_text)
        payout = float(est.get("recommended_payout", 0) or 0)
        if d.get("recommendation") in ("approve", "approve_partial"):
            d["recommended_payout_inr"] = payout
        else:
            d["recommended_payout_inr"] = 0
        for k in ("customer_message_english", "customer_message_local", "headline"):
            if k in d:
                d[k] = d[k].replace("{payout}", inr(payout))
        return d

    def _file_labels(self, llm_request) -> list[tuple[int, str, str]]:
        out = []
        for c in llm_request.contents or []:
            for p in c.parts or []:
                if p.text:
                    for m in re.finditer(r"\[\[FILE (\d+) \| kind=(\w+) \| name=([^\]]+)\]\]", p.text):
                        out.append((int(m.group(1)), m.group(2), m.group(3)))
        return out

    def _generic(self, key: str | None, sys_text: str, llm_request) -> dict:
        files = self._file_labels(llm_request)
        today = re.search(r"Today is (\S+)\.", sys_text)
        today = today.group(1) if today else ""
        note = "(Offline demo model - connect Gemini for a real analysis.)"
        if key == "intake":
            stmt = sys_text.split("<<<")[-1].split(">>>")[0].strip() if "<<<" in sys_text else ""
            return {
                "language": "English", "language_code": "en", "statement_english": stmt or "No statement provided.",
                "incident_date": today, "incident_time": "unknown", "incident_location": "Not stated",
                "incident_type": "collision", "incident_summary": f"Claimant reports damage to the insured vehicle. {note}",
                "vehicle_registration": "", "vehicle_make_model": "",
                "third_party_involved": False, "injuries_reported": False, "police_report_mentioned": False,
                "documents": [{"file_index": i, "file_name": n, "doc_type": "damage_photo" if k == "photo" else "other",
                               "summary": "Uploaded file."} for i, k, n in files],
                "bills": [], "claimed_amount_inr": 0, "non_vehicle_items_claimed": [],
                "missing_information": ["Repair estimate from a workshop"],
            }
        if key == "coverage":
            return {
                "policy_active_on_incident_date": True, "verdict": "covered",
                "items": [{"item": "Accidental damage to the vehicle", "status": "covered", "reason": f"Collision is an insured peril. {note}",
                           "clause_ref": "Sec I.1", "clause_quote": "(f) by accidental external means"}],
                "depreciation_applies": True, "compulsory_deductible_inr": 1000, "conditions_to_verify": [],
                "summary": f"Accidental damage is covered under Section I. {note}",
            }
        if key == "damage":
            photos = [f for f in files if f[1] == "photo"]
            parts = []
            if photos:
                parts.append({"part_code": "rear_bumper", "part_name": "Rear bumper", "file_index": photos[0][0], "box_2d": [450, 250, 800, 750],
                              "severity": "moderate", "action": "repair", "confidence": 0.5, "observation": f"Placeholder finding. {note}"})
            return {
                "photos": [{"file_index": i, "view": "unknown", "quality": "good", "notes": note} for i, _, _ in photos],
                "damaged_parts": parts, "impact_direction": "unclear", "consistent_with_statement": True,
                "consistency_notes": note, "possible_pre_existing_damage": [], "summary": f"Damage review needs Gemini. {note}",
            }
        if key == "fraud":
            score = re.search(r"Rule-based score:\s*(\d+)", sys_text)
            score = int(score.group(1)) if score else 0
            sigs = []
            m = re.search(r"treat their results as hard evidence:\n(\[.*?\n\])", sys_text, re.S)
            if m:
                try:
                    sigs = json.loads(m.group(1))
                except json.JSONDecodeError:
                    sigs = []
            flags = [{"title": s["title"], "severity": s["severity"] if s["severity"] != "none" else "low", "evidence": s["evidence"],
                      "source": "photo_forensics" if "photo" in s["code"] else "billing" if "bill" in s["code"] else "policy_timing"
                      if s["code"] == "policy_timing" else "claim_history"} for s in sigs if s.get("status") == "flag"]
            level = "high" if score >= 70 else "medium" if score >= 30 else "low"
            return {"risk_score": score, "risk_level": level, "red_flags": flags, "document_tampering_suspected": False,
                    "recommended_checks": [] if level == "low" else ["Manual review"], "summary": f"Based on automated checks. {note}"}
        if key == "decision":
            return {
                "recommendation": "approve", "recommended_payout_inr": 0, "confidence": 60, "headline": f"Review recommended. {note}",
                "rationale": [{"point": "Offline model cannot inspect evidence.", "source": "intake", "impact": "neutral"}],
                "next_steps": ["Connect Gemini and re-run the analysis"], "fast_track_eligible": False, "customer_language": "English",
                "customer_message_english": "Thanks for reporting your claim. Our team is reviewing it and a claims officer will confirm the amount shortly.",
                "customer_message_local": "Thanks for reporting your claim. Our team is reviewing it and a claims officer will confirm the amount shortly.",
            }
        return {}

    def _copilot(self, sys_text: str, llm_request) -> str:
        brief = _json_after("Claim summary for orientation:", sys_text)
        question = ""
        for c in reversed(llm_request.contents or []):
            if c.role == "user":
                question = " ".join(p.text or "" for p in c.parts or []).strip()
                if question:
                    break
        dec = brief.get("decision", {})
        est = brief.get("estimate", {})
        lines = ["(Offline demo answer - connect Gemini for real reasoning.)"]
        if dec:
            lines.append(f"AI recommendation: {dec.get('recommendation', '-')} - {dec.get('headline', '')}")
        if est:
            lines.append(f"Estimate: gross {inr(est.get('gross_total', 0))}, depreciation {inr(est.get('depreciation_total', 0))}, "
                         f"deductible {inr(est.get('deductible', 0))}, payable {inr(est.get('recommended_payout', 0))}.")
        q = question.lower()
        if "depreciation" in q or "why" in q:
            lines.append("Depreciation follows Sec I.2: 50% on plastic/rubber parts, nil on glass, age-based on metal; Zero-Dep add-on removes it.")
        if "phone" in q or "mobile" in q:
            lines.append("Mobile phones are personal belongings, excluded under Excl I.4(d).")
        return "\n".join(lines)
