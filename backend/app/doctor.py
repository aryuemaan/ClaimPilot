"""Pre-flight check: `python -m app.doctor` (run from backend/).

Prints the configuration ClaimPilot will use and makes one tiny call to each model,
so you find credential or model-access problems before a demo, not during it.
"""

import asyncio
import json
import warnings

warnings.filterwarnings("ignore")

from . import genai_utils, storage  # noqa: E402
from .config import settings  # noqa: E402


async def main() -> None:
    print("ClaimPilot doctor")
    print("-----------------")
    print(f"Mode:            {settings.mode} ({settings.backend_label})")
    print(f"Gemini model:    {settings.gemini_model}")
    print(f"Adjudicator:     {settings.adjudicator_model}")
    print(f"Gemma (privacy): {settings.gemma_model if settings.gemma_enabled else 'disabled (needs GOOGLE_API_KEY)'}")
    print(f"Thinking level:  {settings.thinking_level or 'model default'}")
    print(f"Storage:         {json.dumps(storage.describe())}")
    print(f"Frontend build:  {'found' if (settings.frontend_dist / 'index.html').exists() else 'missing - run npm run build in frontend/'}")
    if settings.offline:
        print("\nNo credentials found, so the app will run in OFFLINE DEMO MODE.")
        print("Set GOOGLE_API_KEY (https://aistudio.google.com/apikey) in .env to use live Gemini.")
        return
    print("\nCalling models…")
    result = await genai_utils.check_models()
    ok = True
    for model, status in result["results"].items():
        print(f"  {model:28s} {status}")
        if status.startswith("FAILED") and "optional" not in status:
            ok = False
    if settings.gemma_enabled:
        from . import privacy

        sample = "The other driver's number is 98480 12345. I live at Flat 402, Lake View Apartments, Kondapur."
        r = await privacy.redact(sample)
        print(f"\nPrivacy pass:    Gemma {r['gemma_status']} -> {r['masked_text']}")
    if not ok:
        print("\nFix: check the key/project, or set GEMINI_MODEL to a model your account can use (e.g. gemini-3.6-flash).")
        print("If the error mentions thinking_level, set THINKING_LEVEL= (empty) for that model.")
    else:
        print("\nAll good - you're ready to demo.")


if __name__ == "__main__":
    asyncio.run(main())
