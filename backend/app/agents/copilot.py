"""'Ask ClaimPilot' - a tool-using ADK agent that answers questions about one claim.

Two audiences share the same agent code with different instructions and tools:
  adjuster  - full claim file, including fraud evidence
  customer  - plain-language answers about their own claim; fraud data is never exposed
"""

from __future__ import annotations

import json
import uuid

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import ToolContext
from google.genai import types

from ..demo import policy_pdf
from . import prompts
from .pipeline import gen_config, make_model

_sessions = InMemorySessionService()

CUSTOMER_SECTIONS = {"summary", "coverage", "damage", "estimate", "status", "documents"}
ADJUSTER_SECTIONS = CUSTOMER_SECTIONS | {"fraud", "decision", "timeline", "privacy"}


def claim_brief(claim: dict, audience: str) -> dict:
    ai = claim.get("ai") or {}
    dec = ai.get("decision") or {}
    est = ai.get("estimate") or {}
    brief = {
        "claim_id": claim.get("id"),
        "status": claim.get("status"),
        "policy_number": claim.get("policy_number"),
        "vehicle": claim.get("vehicle"),
        "incident": (ai.get("intake") or {}).get("incident_summary"),
        "estimate": {k: est.get(k) for k in ("gross_total", "depreciation_total", "deductible", "recommended_payout", "zero_dep")},
        "final_decision": claim.get("final_decision"),
    }
    if audience == "adjuster":
        brief["decision"] = {k: dec.get(k) for k in ("recommendation", "headline", "confidence", "recommended_payout_inr")}
        brief["fraud"] = {k: (ai.get("fraud") or {}).get(k) for k in ("risk_score", "risk_level", "summary")}
    return brief


def _section(claim: dict, section: str, audience: str) -> dict:
    ai = claim.get("ai") or {}
    allowed = ADJUSTER_SECTIONS if audience == "adjuster" else CUSTOMER_SECTIONS
    if section not in allowed:
        return {"error": f"Section '{section}' is not available. Available: {sorted(allowed)}"}
    if section == "summary":
        return claim_brief(claim, audience)
    if section == "status":
        return {"status": claim.get("status"), "final_decision": claim.get("final_decision"), "timeline": claim.get("timeline", [])}
    if section == "documents":
        return {"files": [{"index": f.get("index"), "name": f["name"], "kind": f["kind"]} for f in claim.get("files", [])],
                "extracted": (ai.get("intake") or {}).get("documents", []), "bills": (ai.get("intake") or {}).get("bills", [])}
    if section == "fraud":
        return {"assessment": ai.get("fraud"), "signals": (ai.get("fraud_signals") or {}).get("signals", [])}
    if section == "timeline":
        return {"timeline": claim.get("timeline", []), "audit": claim.get("audit", [])}
    data = ai.get(section) or {}
    if audience == "customer" and section == "damage":
        data = {k: data.get(k) for k in ("damaged_parts", "summary")}
    return data


async def ask(claim: dict, policy: dict, question: str, audience: str) -> str:
    audience = "customer" if audience == "customer" else "adjuster"

    def get_claim_file(section: str, tool_context: ToolContext) -> dict:
        """Read one section of this claim's file.

        Args:
            section: one of summary, status, documents, coverage, damage, estimate, fraud, decision, timeline, privacy.
        """
        return _section(claim, section.strip().lower(), audience)

    def search_policy_wording(query: str) -> dict:
        """Search the policy wording for clauses about a topic, e.g. 'depreciation plastic', 'mobile phone', 'survey before repair'.

        Args:
            query: a few keywords describing the topic.
        """
        return {"clauses": policy_pdf.search_wording(query)}

    history = (claim.get("chat") or {}).get(audience, [])[-8:]
    state = {
        "claim_id": claim["id"],
        "today": claim.get("reported_on"),
        "audience": audience,
        "policy": {k: v for k, v in policy.items() if k != "wording_text"},
        "brief": claim_brief(claim, audience),
    }

    def instruction(ctx):
        base = prompts.copilot(dict(ctx.state))
        if history:
            convo = "\n".join(f"{m['role']}: {m['text']}" for m in history)
            base += f"\nConversation so far:\n{convo}\n"
        return base

    agent = LlmAgent(
        name="claim_copilot",
        model=make_model(),
        instruction=instruction,
        tools=[get_claim_file, search_policy_wording],
        generate_content_config=gen_config(),
    )
    runner = Runner(app_name="claimpilot_copilot", agent=agent, session_service=_sessions)
    session = await _sessions.create_session(app_name="claimpilot_copilot", user_id=claim["id"], state=state,
                                             session_id=uuid.uuid4().hex)
    answer = ""
    async for event in runner.run_async(user_id=claim["id"], session_id=session.id,
                                        new_message=types.Content(role="user", parts=[types.Part.from_text(text=question)])):
        if event.is_final_response() and event.content and event.content.parts:
            answer = "".join(p.text or "" for p in event.content.parts if not getattr(p, "thought", False)).strip()
    await _sessions.delete_session(app_name="claimpilot_copilot", user_id=claim["id"], session_id=session.id)
    return answer or "I couldn't find an answer in the claim file."


def to_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)
