"""End-to-end tests for the agent pipeline.

test_offline_pipeline  - full ADK pipeline with the scripted offline model.
test_live_wiring       - flips to live Gemini mode and intercepts HTTP at the
                         google-genai transport layer. This exercises the real
                         ADK Gemini model class, request building, schema
                         conversion, file routing and tool calling, without
                         network access or an API key.

Run:  cd backend && python -m pytest -q
"""

from __future__ import annotations

import asyncio
import json
import re

import pytest

from app import main, storage
from app.agents import copilot, offline, pipeline
from app.config import settings
from app.demo import seed


def run(coro):
    return asyncio.run(coro)


async def _claim_from_kit(key: str) -> str:
    kit = await storage.docs.get("samples", key)
    uploads = []
    for f in kit["files"]:
        data, mime = await storage.files.load(f["key"])
        uploads.append((f["name"], f["kind"], data, mime))
    return await main._create_claim(kit["policy_number"], kit["statement"], kit["language"], uploads, channel="test")


@pytest.fixture(scope="module", autouse=True)
def seeded():
    run(seed.seed())
    yield


def test_offline_pipeline():
    async def go():
        ids = {k: await _claim_from_kit(k) for k in ("genuine", "partial", "fraud")}
        for cid in ids.values():
            await pipeline.run_claim(cid)
        return {k: await storage.docs.get("claims", v) for k, v in ids.items()}

    claims = run(go())
    g, p, f = claims["genuine"], claims["partial"], claims["fraud"]
    for c in claims.values():
        assert c["status"] == "review", c.get("error")
        assert all(s["status"] == "done" for s in c["trace"])

    assert g["ai"]["decision"]["recommendation"] == "approve"
    assert g["ai"]["estimate"]["recommended_payout"] == 11124
    assert g["fast_track"] is True
    assert g["ai"]["privacy"]["findings"][0]["type"] == "phone"

    assert p["ai"]["decision"]["recommendation"] == "approve_partial"
    assert p["ai"]["estimate"]["depreciation_total"] == 0  # zero-dep add-on
    assert p["ai"]["privacy"]["findings"][0]["type"] == "aadhaar"

    flagged = {s["code"] for s in f["ai"]["fraud_signals"]["signals"] if s["status"] == "flag"}
    assert {"duplicate_photo", "photo_metadata", "policy_timing", "bill_math", "bill_dates", "claim_history"} <= flagged
    assert f["ai"]["decision"]["recommendation"] == "investigate"
    assert f["ai"]["decision"]["recommended_payout_inr"] == 0


# ---------------------------------------------------------------------------
# Live wiring with a fake Gemini HTTP endpoint
# ---------------------------------------------------------------------------

CAPTURED: list[dict] = []


def _gemini_body(text: str | None = None, function_call: dict | None = None) -> str:
    part = {"text": text} if text is not None else {"functionCall": function_call}
    return json.dumps({
        "candidates": [{"content": {"role": "model", "parts": [part]}, "finishReason": "STOP"}],
        "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 50, "totalTokenCount": 150},
        "modelVersion": "fake",
    })


def _mime(part: dict) -> str:
    d = part.get("inlineData") or part.get("inline_data") or {}
    return d.get("mimeType") or d.get("mime_type") or ""


def _system_text(req: dict) -> str:
    si = req.get("systemInstruction") or req.get("system_instruction") or {}
    return "".join(p.get("text", "") for p in si.get("parts", []))


def _fake_reply(url: str, req: dict) -> str:
    sys_text = _system_text(req)
    contents = req.get("contents", [])
    mimes = [_mime(p) for c in contents for p in c.get("parts", []) if "inlineData" in p or "inline_data" in p]
    role = (re.search(r"ROLE:\s*(\S+)", sys_text) or [None, ""])[1]
    CAPTURED.append({"url": url, "role": role, "mimes": mimes, "config": req.get("generationConfig", {}), "tools": bool(req.get("tools"))})

    if "gemma" in url:
        return _gemini_body('{"items": []}')
    if role.startswith("copilot"):
        has_response = any("functionResponse" in p for c in contents for p in c.get("parts", []))
        if not has_response:
            return _gemini_body(function_call={"name": "get_claim_file", "args": {"section": "estimate"}})
        return _gemini_body("The payout is the repair cost less depreciation and the deductible (Sec I.2, Sec I.3).")
    key = offline._ROLE_TO_KEY.get(role)
    if key:
        claim_id = re.search(r"Claim ID:\s*(\S+)", sys_text).group(1)
        payload = json.loads(json.dumps(SCRIPTS_BY_CLAIM[claim_id][key]))
        if key == "decision":
            payload = offline.OfflineDemoLlm(fast=True)._fill_decision(payload, sys_text)
        return _gemini_body(json.dumps(payload, ensure_ascii=False))
    if "Transcribe" in json.dumps(contents):
        return _gemini_body(json.dumps({"language": "Telugu", "language_code": "te", "transcript": "నా కారు", "english": "My car"}))
    return _gemini_body("అనువాదం")  # translation request


SCRIPTS_BY_CLAIM: dict[str, dict] = {}


def test_live_wiring(monkeypatch):
    from google.genai import _api_client

    async def fake_once(self, http_request, stream=False):
        body = json.loads(http_request.data) if isinstance(http_request.data, (str, bytes)) else http_request.data
        return _api_client.HttpResponse(headers={}, response_stream=[_fake_reply(http_request.url, body)])

    monkeypatch.setattr(_api_client.BaseApiClient, "_async_request_once", fake_once)
    monkeypatch.setattr(settings, "offline", False)
    monkeypatch.setattr(settings, "api_key", "test-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setattr(pipeline, "_runner", None)
    CAPTURED.clear()

    async def go():
        out = {}
        for key in ("genuine", "fraud"):
            cid = await _claim_from_kit(key)
            kit = await storage.docs.get("samples", key)
            SCRIPTS_BY_CLAIM[cid] = kit["offline"]
            await pipeline.run_claim(cid)
            out[key] = await storage.docs.get("claims", cid)
        claim = out["genuine"]
        policy = await storage.docs.get("policies", claim["policy_number"])
        answer = await copilot.ask(claim, policy, "Why is the payout lower?", "adjuster")
        from app import genai_utils

        tr = await genai_utils.transcribe(b"RIFF....WAVEfmt ", "audio/wav", "te")
        upd = await genai_utils.customer_update(action="request_info", amount="₹0", note="Please send the FIR", first_name="Ravi",
                                                claim_id=claim["id"], language_name="Telugu", workshop=None)
        return out, answer, tr, upd

    try:
        out, answer, tr, upd = run(go())
    finally:
        pipeline._runner = None

    for c in out.values():
        assert c["status"] == "review", c.get("error")
        assert c["model"]["model"] == settings.gemini_model
    assert out["genuine"]["ai"]["decision"]["recommendation"] == "approve"
    assert out["fraud"]["ai"]["decision"]["recommendation"] == "investigate"

    by_role = {}
    for c in CAPTURED:
        by_role.setdefault(c["role"], []).append(c)
    # each agent sees only the files it needs
    assert all(m == "image/jpeg" for m in by_role["damage_agent"][0]["mimes"])
    assert by_role["coverage_agent"][0]["mimes"] == ["application/pdf"]
    assert by_role["adjudicator"][0]["mimes"] == []
    assert len(by_role["intake_agent"][0]["mimes"]) == 3
    # structured output + thinking level are sent to Gemini
    cfg = by_role["intake_agent"][0]["config"]
    assert cfg.get("responseMimeType") == "application/json"
    assert "responseSchema" in cfg or "responseJsonSchema" in cfg
    tc = cfg.get("thinkingConfig", {})
    assert str(tc.get("thinkingLevel") or tc.get("thinking_level")).endswith("LOW")
    # Gemma privacy pass was called
    assert any("gemma" in c["url"] for c in CAPTURED)
    # copilot used a tool and answered
    assert by_role["copilot_adjuster"][0]["tools"] is True
    assert "depreciation" in answer
    assert tr["english"] == "My car"
    assert upd["local"] == "అనువాదం"
