"""Seeds demo policies, claim history and sample claim kits into the stores.

Runs automatically on first start (AUTO_SEED=true) and from the console's
"Reset demo" button. Dates are generated relative to today.
"""

from __future__ import annotations

import io
import logging
from datetime import date, datetime

from PIL import Image, ImageOps

from .. import storage
from ..fraud_checks import multi_hash
from ..timeutil import now_iso
from . import policy_pdf, render, scenarios

log = logging.getLogger("claimpilot.seed")

PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def _real_photos(scenario: str) -> list[bytes]:
    """Photos dropped into sample-data/photos/<scenario>/ override the illustrations."""
    from ..config import settings

    folder = settings.sample_photos_dir / scenario
    if not folder.is_dir():
        return []
    out = []
    for p in sorted(folder.iterdir()):
        if p.suffix.lower() in PHOTO_EXT:
            out.append(p.read_bytes())
    return out[:4]


def _normalise(photo: bytes, taken: datetime | None) -> bytes:
    img = Image.open(io.BytesIO(photo))
    img = ImageOps.exif_transpose(img).convert("RGB")
    if max(img.size) > 1800:
        img.thumbnail((1800, 1800))
    return render.to_jpeg(img, taken_at=taken)


def _render_photo(spec: dict, rendered: list[Image.Image]) -> Image.Image:
    if spec["render"] == "rear":
        return render.render_rear_photo(color=spec["color"], plate=spec["plate"], damage_side=spec["side"], seed=spec["seed"])
    if spec["render"] == "side":
        return render.render_side_photo(color=spec["color"], seed=spec["seed"])
    if spec["render"] == "crop":
        return render.crop_zoom(rendered[spec["of"]], spec["box"])
    raise ValueError(spec["render"])


async def seed(today: date | None = None, *, wipe_claims: bool = True) -> dict:
    today = today or date.today()
    docs, files = storage.docs, storage.files
    log.info("Seeding demo data for %s", today)

    if wipe_claims:
        await docs.clear("claims")
        await files.delete_prefix("claims")
    for coll in ("policies", "past_claims", "samples"):
        await docs.clear(coll)

    scen = scenarios.build(today)
    history = scenarios.history_claims(today)

    # --- photo that the fraud scenario "borrows" from an old claim ------------
    fraud = scen["fraud"]
    hp = fraud["history_photo"]
    real_fraud = _real_photos("fraud")
    if real_fraud:
        history_jpeg = _normalise(real_fraud[0], hp["taken"])
    else:
        history_jpeg = render.to_jpeg(
            render.render_rear_photo(color=hp["color"], plate=hp["plate"], damage_side=hp["side"], seed=hp["seed"]),
            taken_at=hp["taken"],
        )
    vikram = next(h for h in history if h["id"] == "CLM-HIST-0412")
    await files.save("past_claims/CLM-HIST-0412/rear.jpg", history_jpeg, "image/jpeg")
    vikram["photos"].append({"photo_id": "rear.jpg", "key": "past_claims/CLM-HIST-0412/rear.jpg", "hashes": multi_hash(history_jpeg)})

    # a few more historical photos so the duplicate search has a real haystack
    extra = [("CLM-HIST-0480", "rear", (40, 40, 44), "TS 09 FT 7710", "right", 21),
             ("CLM-HIST-0526", "rear", (235, 235, 230), "TS 10 EK 3381", "left", 33),
             ("CLM-HIST-0491", "rear", (120, 30, 40), "TS 12 EP 4422", "left", 41)]
    for cid, kind, color, plate, side, seed_ in extra:
        img = (render.render_rear_photo(color=color, plate=plate, damage_side=side, seed=seed_, daylight=False) if kind == "rear"
               else render.render_side_photo(color=color, seed=seed_))
        jpeg = render.to_jpeg(img)
        key = f"past_claims/{cid}/rear.jpg"
        await files.save(key, jpeg, "image/jpeg")
        next(h for h in history if h["id"] == cid)["photos"].append({"photo_id": "rear.jpg", "key": key, "hashes": multi_hash(jpeg)})

    for h in history:
        await docs.put("past_claims", h["id"], h)

    # --- policies + sample kits -----------------------------------------------
    for key, sc in scen.items():
        pol = dict(sc["policy"])
        pdf = policy_pdf.render_policy_pdf(pol)
        pdf_key = f"policies/{pol['policy_number']}.pdf"
        await files.save(pdf_key, pdf, "application/pdf")
        pol["pdf_key"] = pdf_key
        pol["wording_text"] = policy_pdf.wording_text()
        pol["claims_last_12m"] = sum(
            1 for h in history
            if h["holder_name"] == pol["holder_name"] and (today - date.fromisoformat(h["incident_date"])).days <= 365
        )
        pol["scenario"] = key
        await docs.put("policies", pol["policy_number"], pol)

        kit_files = []
        real = _real_photos(key) if key != "fraud" else []
        rendered: list[Image.Image] = []
        for i, ph in enumerate(sc["photos"]):
            name = ph["name"]
            if ph["render"] == "reuse":
                jpeg = render.reuse_variant(history_jpeg, seed=i, **ph["variant"])
            elif real:
                if i >= len(real):
                    continue
                jpeg = _normalise(real[i], ph.get("taken"))
            else:
                img = _render_photo(ph, rendered)
                rendered.append(img)
                jpeg = render.to_jpeg(img, taken_at=ph.get("taken"))
            fkey = f"samples/{key}/{name}"
            await files.save(fkey, jpeg, "image/jpeg")
            kit_files.append({"name": name, "kind": "photo", "mime": "image/jpeg", "key": fkey})
        for b in sc["bills"]:
            img = render.render_bill(b, seed=len(b["name"]))
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=88)
            fkey = f"samples/{key}/{b['name']}"
            await files.save(fkey, buf.getvalue(), "image/jpeg")
            kit_files.append({"name": b["name"], "kind": "document", "mime": "image/jpeg", "key": fkey})

        await docs.put("samples", key, {
            "key": key,
            "title": sc["title"],
            "blurb": sc["blurb"],
            "policy_number": pol["policy_number"],
            "holder_name": pol["holder_name"],
            "first_name": pol["first_name"],
            "language": pol["language"],
            "language_name": pol["language_name"],
            "vehicle": pol["vehicle"]["make_model"],
            "registration": pol["vehicle"]["registration"],
            "statement": sc["statement"],
            "incident": sc["incident"],
            "files": kit_files,
            "uses_real_photos": bool(real) or (key == "fraud" and bool(real_fraud)),
            "offline": sc["offline"],
        })

    await docs.put("meta", "seed", {"seeded_on": today.isoformat(), "at": now_iso()})
    log.info("Seed complete")
    return {"seeded_on": today.isoformat(), "policies": len(scen), "past_claims": len(history)}


async def ensure_seeded() -> None:
    meta = await storage.docs.get("meta", "seed")
    if not meta:
        await seed(wipe_claims=False)
