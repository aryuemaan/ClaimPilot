"""Direct Gemini calls outside the agent pipeline: voice transcription and status updates."""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from .config import settings

log = logging.getLogger("claimpilot.genai")

LANG_NAMES = {"en": "English", "hi": "Hindi", "te": "Telugu", "ta": "Tamil", "kn": "Kannada", "mr": "Marathi", "bn": "Bengali"}


class Transcript(BaseModel):
    language: str = Field(description="Language spoken, e.g. Telugu")
    language_code: str = Field(description="ISO 639-1 code")
    transcript: str = Field(description="Exact transcript in the original language and native script")
    english: str = Field(description="Faithful English translation")


def _client():
    from google import genai

    if settings.use_vertex:
        return genai.Client(vertexai=True, project=settings.project or None, location=settings.location)
    return genai.Client(api_key=settings.api_key)


def _config(schema=None):
    from google.genai import types

    kw = {}
    if schema is not None:
        kw.update(response_mime_type="application/json", response_schema=schema)
    if settings.thinking_level:
        kw["thinking_config"] = types.ThinkingConfig(thinking_level=settings.thinking_level.upper())
    return types.GenerateContentConfig(**kw)


async def transcribe(audio: bytes, mime: str, hint_language: str | None) -> dict:
    if settings.offline:
        raise RuntimeError("offline")
    from google.genai import types

    hint = f" The speaker most likely uses {LANG_NAMES.get(hint_language or '', hint_language)}." if hint_language else ""
    prompt = (
        "This is a voice note from a car-insurance customer in India describing an accident or damage to their car."
        f"{hint} Transcribe it exactly in the language and native script spoken (keep English words as spoken), "
        "then translate it faithfully into English. Do not add anything that was not said."
    )
    resp = await _client().aio.models.generate_content(
        model=settings.gemini_model,
        contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt), types.Part.from_bytes(data=audio, mime_type=mime)])],
        config=_config(Transcript),
    )
    return Transcript.model_validate_json(resp.text).model_dump()


_TEMPLATES = {
    "approve": "Good news, {name}: your claim {claim} has been approved for {amount}. {extra}",
    "approve_partial": "{name}, your claim {claim} has been approved for {amount}. Some items were not covered, as explained in your claim summary. {extra}",
    "request_info": "{name}, to continue with claim {claim} we need a little more from you: {note}",
    "investigate": "{name}, a claims officer will contact you within one working day to arrange an inspection for claim {claim}. Please keep the damaged parts and original bills.",
    "reject": "{name}, we're sorry - claim {claim} could not be approved. Reason: {note} You can reply here if you'd like us to review it again.",
}


_LOCAL_TEMPLATES = {
    "Telugu": {
        "approve": "శుభవార్త, {name} గారు: మీ క్లెయిమ్ {claim} కు {amount} ఆమోదించబడింది. {extra}",
        "approve_partial": "{name} గారు, మీ క్లెయిమ్ {claim} కు {amount} ఆమోదించబడింది. కొన్ని అంశాలు కవర్ కాలేదు - వివరాలు మీ క్లెయిమ్ సారాంశంలో ఉన్నాయి. {extra}",
        "request_info": "{name} గారు, క్లెయిమ్ {claim} ను కొనసాగించడానికి మాకు ఇంకా కొంత సమాచారం కావాలి: {note}",
        "investigate": "{name} గారు, క్లెయిమ్ {claim} కోసం వాహన తనిఖీ ఏర్పాటు చేయడానికి ఒక క్లెయిమ్ అధికారి ఒక పని దినంలో మిమ్మల్ని సంప్రదిస్తారు. దెబ్బతిన్న భాగాలు మరియు అసలు బిల్లులను దయచేసి భద్రపరచండి.",
        "reject": "{name} గారు, క్షమించండి - క్లెయిమ్ {claim} ఆమోదించబడలేదు. కారణం: {note}",
        "cashless": "మేము ఈ మొత్తాన్ని నేరుగా {workshop} కు చెల్లిస్తాము (క్యాష్‌లెస్).",
        "bank": "ఈ మొత్తం 2 పని దినాల్లో మీ రిజిస్టర్డ్ బ్యాంక్ ఖాతాకు జమ అవుతుంది.",
    },
    "Hindi": {
        "approve": "खुशखबरी, {name} जी: आपका क्लेम {claim} {amount} के लिए मंज़ूर हो गया है। {extra}",
        "approve_partial": "{name} जी, आपका क्लेम {claim} {amount} के लिए मंज़ूर हो गया है। कुछ चीज़ें कवर नहीं थीं - विवरण आपके क्लेम सारांश में है। {extra}",
        "request_info": "{name} जी, क्लेम {claim} आगे बढ़ाने के लिए हमें थोड़ी और जानकारी चाहिए: {note}",
        "investigate": "{name} जी, क्लेम {claim} के लिए गाड़ी के निरीक्षण की व्यवस्था करने हेतु एक क्लेम अधिकारी एक कार्य दिवस में आपसे संपर्क करेंगे। कृपया खराब हुए पार्ट्स और मूल बिल संभाल कर रखें।",
        "reject": "{name} जी, हमें खेद है - क्लेम {claim} मंज़ूर नहीं हो सका। कारण: {note}",
        "cashless": "हम यह राशि सीधे {workshop} को चुकाएँगे (कैशलेस)।",
        "bank": "यह राशि 2 कार्य दिवसों में आपके रजिस्टर्ड बैंक खाते में आ जाएगी।",
    },
}


def _template_local(language_name: str, action: str, **kw) -> str | None:
    t = _LOCAL_TEMPLATES.get(language_name)
    if not t:
        return None
    extra = t["cashless"].format(**kw) if kw.get("workshop") else t["bank"]
    return t.get(action, t["approve"]).format(extra=extra, **kw).strip()


async def customer_update(*, action: str, amount: str, note: str, first_name: str, claim_id: str, language_name: str,
                          workshop: str | None) -> dict:
    extra = f"We'll settle it directly with {workshop} (cashless)." if workshop else "Payment will reach your registered bank account within 2 working days."
    english = _TEMPLATES.get(action, _TEMPLATES["approve"]).format(name=first_name, claim=claim_id, amount=amount, note=note or "", extra=extra).strip()
    local = _template_local(language_name, action, name=first_name, claim=claim_id, amount=amount, note=note or "",
                            workshop=workshop) or english
    if not settings.offline and language_name and language_name.lower() != "english" and (note or language_name not in _LOCAL_TEMPLATES):
        try:
            resp = await _client().aio.models.generate_content(
                model=settings.gemini_model,
                contents=(f"Translate this message from an insurance company to its customer into {language_name}, in native script. "
                          f"Keep the claim number, the ₹ amount and names exactly as they are. Reply with the translation only.\n\n{english}"),
                config=_config(),
            )
            local = (resp.text or english).strip()
        except Exception as exc:
            log.warning("Translation failed: %s", exc)
    return {"english": english, "local": local}


async def check_models() -> dict:
    """Used by `python -m app.doctor` to verify credentials and model access."""
    out = {"mode": settings.mode, "backend": settings.backend_label, "gemini_model": settings.gemini_model, "results": {}}
    if settings.offline:
        return out
    client = _client()
    for name in {settings.gemini_model, settings.adjudicator_model}:
        try:
            r = await client.aio.models.generate_content(model=name, contents="Reply with the single word: ready", config=_config())
            out["results"][name] = f"ok ({(r.text or '').strip()[:20]})"
        except Exception as exc:
            out["results"][name] = f"FAILED: {exc}"
    if settings.gemma_enabled:
        from google import genai

        try:
            g = genai.Client(api_key=settings.api_key, vertexai=False)
            r = await g.aio.models.generate_content(model=settings.gemma_model, contents="Reply with the single word: ready")
            out["results"][settings.gemma_model] = f"ok ({(r.text or '').strip()[:20]})"
        except Exception as exc:
            out["results"][settings.gemma_model] = f"FAILED (optional): {exc}"
    return out
