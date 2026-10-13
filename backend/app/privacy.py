"""PII redaction: deterministic rules first, then an optional Gemma pass.

Rules catch structured identifiers (Aadhaar, PAN, phone, email, card and bank
numbers). Gemma then looks for free-text personal details the rules can't see
(home addresses, third-party names with phone numbers spelled out, etc.).
Vehicle registration numbers are intentionally kept - the claim needs them.
"""

from __future__ import annotations

import json
import logging
import re

from .config import settings

log = logging.getLogger("claimpilot.privacy")

_RULES: list[tuple[str, re.Pattern, callable]] = []


def _keep_last(n: int):
    def f(m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group(0))
        return "•" * max(0, len(digits) - n) + digits[-n:]
    return f


_RULES = [
    # Aadhaar: 12 digits, first digit 2-9, often grouped 4-4-4.
    ("aadhaar", re.compile(r"(?<!\d)[2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4}(?!\d)"), lambda m: "[Aadhaar ••••" + re.sub(r"\D", "", m.group(0))[-4:] + "]"),
    # Payment card numbers (13-16 digits, optional separators).
    ("card", re.compile(r"(?<!\d)(?:\d[ -]?){12,15}\d(?!\d)"), lambda m: "[card ••••" + re.sub(r"\D", "", m.group(0))[-4:] + "]"),
    # PAN: AAAAA9999A
    ("pan", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), lambda m: "[PAN ••••" + m.group(0)[-5:-1] + "]"),
    # Indian mobile numbers with optional +91 / 0 prefix and a space in the middle.
    ("phone", re.compile(r"(?<!\d)(?:\+?91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?!\d)"), lambda m: "[phone ••••" + re.sub(r"\D", "", m.group(0))[-4:] + "]"),
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), lambda m: "[email]"),
    # Bank account numbers mentioned with an account keyword.
    ("bank_account", re.compile(r"(?i)(?:a/c|account|acct)\s*(?:no\.?|number)?\s*[:#-]?\s*(\d{9,18})"), lambda m: m.group(0).replace(m.group(1), "••••" + m.group(1)[-4:])),
]


def rule_mask(text: str) -> tuple[str, list[dict]]:
    found: list[dict] = []
    out = text
    for kind, pattern, repl in _RULES:
        def _sub(m: re.Match, kind=kind, repl=repl) -> str:
            masked = repl(m)
            found.append({"type": kind, "masked_as": masked, "by": "rules"})
            return masked
        out = pattern.sub(_sub, out)
    return out, found


_GEMMA_PROMPT = """You are a privacy filter for an insurance company in India.
Find personal details in the claimant's message that should NOT be shared with
downstream systems: full home addresses, house/flat numbers, other people's
phone numbers or ID numbers written in words, bank or UPI IDs, dates of birth.
Do NOT flag: the claimant's first name, vehicle registration numbers, place or
road names where the incident happened, workshop names, amounts.
Text that already looks like [phone ••••1234] is already masked - ignore it.

Return ONLY JSON: {"items": [{"text": "<exact substring>", "type": "<address|id|phone|bank|dob|other>"}]}
Return {"items": []} if nothing needs masking.

Message:
"""


async def gemma_mask(text: str) -> tuple[str, list[dict], str]:
    """Returns (masked_text, findings, status). Never raises."""
    if not settings.gemma_enabled or not text.strip():
        return text, [], "skipped"
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.api_key, vertexai=False)
        try:
            # Gemma 4 can think; for a quick classification task we switch it off.
            resp = await client.aio.models.generate_content(
                model=settings.gemma_model,
                contents=_GEMMA_PROMPT + text,
                config=types.GenerateContentConfig(
                    temperature=0.0, max_output_tokens=1024,
                    thinking_config=types.ThinkingConfig(thinking_level="MINIMAL"),
                ),
            )
        except Exception as first:  # older Gemma versions reject thinking settings
            log.info("Gemma call without thinking config (%s)", type(first).__name__)
            resp = await client.aio.models.generate_content(
                model=settings.gemma_model,
                contents=_GEMMA_PROMPT + text,
                config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=1024),
            )
        raw = (resp.text or "").strip()
        raw = raw[raw.find("{"): raw.rfind("}") + 1] if "{" in raw else '{"items": []}'
        items = json.loads(raw).get("items", [])
        findings = []
        for item in items:
            s = (item.get("text") or "").strip()
            if len(s) < 4 or s not in text:
                continue
            kind = item.get("type", "other")
            text = text.replace(s, f"[{kind} redacted]")
            findings.append({"type": kind, "masked_as": f"[{kind} redacted]", "by": "gemma"})
        return text, findings, "ok"
    except Exception as exc:  # Gemma is a best-effort extra layer
        log.warning("Gemma privacy pass failed: %s", exc)
        return text, [], f"unavailable ({type(exc).__name__})"


async def redact(text: str) -> dict:
    masked, findings = rule_mask(text or "")
    masked, gemma_findings, gemma_status = await gemma_mask(masked)
    findings += gemma_findings
    return {
        "masked_text": masked,
        "findings": findings,
        "counts": _count(findings),
        "gemma_status": gemma_status,
        "gemma_model": settings.gemma_model if settings.gemma_enabled else None,
    }


def _count(findings: list[dict]) -> dict:
    c: dict[str, int] = {}
    for f in findings:
        c[f["type"]] = c.get(f["type"], 0) + 1
    return c
