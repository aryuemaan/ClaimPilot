"""Deterministic fraud signals ("tools" for the fraud analyst agent).

Each check returns a signal dict:
  {code, title, status: pass|flag|info, severity: none|low|medium|high,
   weight, evidence, data}
The fraud analyst LLM gets these as hard evidence and adds what only a model
can see (tampered-looking documents, story inconsistencies).
"""

from __future__ import annotations

import io
from datetime import date, datetime

from PIL import Image, ImageOps

# ---------------------------------------------------------------------------
# Perceptual hashing (dHash 16x16 = 256 bits). Robust to resizing, recompression,
# small crops and brightness changes - the usual tricks when a photo is reused.
# ---------------------------------------------------------------------------

HASH_SIZE = 16
# Crop windows (left, top, right-margin, bottom-margin) so a photo that was re-saved with a
# crop of up to ~12% still matches the original.
_EDGES = (0.0, 0.03, 0.06, 0.09, 0.12)
_FAR = (0.0, 0.03, 0.06)


def _dhash_gray(img: Image.Image) -> str:
    img = img.resize((HASH_SIZE + 1, HASH_SIZE), Image.Resampling.LANCZOS)
    px = img.tobytes()
    w = HASH_SIZE + 1
    bits = 0
    for row in range(HASH_SIZE):
        for col in range(HASH_SIZE):
            bits = (bits << 1) | (1 if px[row * w + col] > px[row * w + col + 1] else 0)
    return f"{bits:0{HASH_SIZE * HASH_SIZE // 4}x}"


def multi_hash(image_bytes: bytes) -> list[str]:
    """dHash of the full frame (index 0) followed by hashes of shifted crops."""
    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img).convert("L")
    img = img.resize((320, max(1, int(320 * img.height / img.width))), Image.Resampling.BILINEAR)
    w, h = img.size
    out = [_dhash_gray(img)]
    for l in _EDGES:
        for t in _EDGES:
            for r in _FAR:
                for b in _FAR:
                    if l == t == r == b == 0:
                        continue
                    out.append(_dhash_gray(img.crop((int(w * l), int(h * t), int(w * (1 - r)), int(h * (1 - b))))))
    return out


def dhash(image_bytes: bytes) -> str:
    return multi_hash(image_bytes)[0]


def best_similarity(a: list[str], b: list[str]) -> float:
    """Max similarity between full frame of one photo and any crop of the other (both ways)."""
    if not a or not b:
        return 0.0
    return max(max(hash_similarity(a[0], y) for y in b), max(hash_similarity(x, b[0]) for x in a))


def hash_similarity(a: str, b: str) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    distance = bin(int(a, 16) ^ int(b, 16)).count("1")
    return 1.0 - distance / (len(a) * 4)


def exif_datetime(image_bytes: bytes) -> datetime | None:
    try:
        img = Image.open(io.BytesIO(image_bytes))
        exif = img.getexif()
        raw = exif.get_ifd(0x8769).get(36867) or exif.get(306)  # DateTimeOriginal / DateTime
        if not raw:
            return None
        return datetime.strptime(str(raw).strip()[:19], "%Y:%m:%d %H:%M:%S")
    except Exception:
        return None


def _parse_date(value: str | None) -> date | None:
    if not value or value == "unknown":
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(value.strip()[:11].strip(), fmt).date()
        except ValueError:
            continue
    return None


def _signal(code, title, status, severity, weight, evidence, data=None) -> dict:
    return {
        "code": code,
        "title": title,
        "status": status,
        "severity": severity,
        "weight": weight,
        "evidence": evidence,
        "data": data or {},
    }


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def check_duplicate_photos(photo_hashes: list[dict], history: list[dict], threshold: float = 0.86) -> dict:
    """photo_hashes: [{file_id, name, hashes}]; history: past claims with photo hash lists."""
    best = None
    for ph in photo_hashes:
        for past in history:
            for past_photo in past.get("photos", []):
                sim = best_similarity(ph.get("hashes", []), past_photo.get("hashes", []))
                if sim >= threshold and (best is None or sim > best["similarity"]):
                    best = {
                        "similarity": round(sim, 3),
                        "file_id": ph["file_id"],
                        "file_name": ph["name"],
                        "past_claim_id": past["id"],
                        "past_claimant": past.get("claimant_masked", "another policyholder"),
                        "past_vehicle": past.get("vehicle", ""),
                        "past_date": past.get("incident_date", ""),
                        "past_photo_id": past_photo.get("photo_id", ""),
                    }
    if best:
        return _signal(
            "duplicate_photo",
            "Photo matches an earlier claim",
            "flag",
            "high",
            45,
            f"'{best['file_name']}' is {best['similarity']:.0%} visually identical to a photo in claim "
            f"{best['past_claim_id']} ({best['past_vehicle']}, {best['past_date']}).",
            best,
        )
    return _signal("duplicate_photo", "Photos are original", "pass", "none", 0,
                   f"{len(photo_hashes)} photo(s) compared against {sum(len(p.get('photos', [])) for p in history)} photos from past claims - no match.")


def check_photo_dates(photo_meta: list[dict], incident: date | None, policy_start: date | None) -> dict:
    dated = [p for p in photo_meta if p.get("taken_at")]
    if not dated:
        return _signal("photo_metadata", "Photo capture dates unavailable", "info", "none", 0,
                       "No camera timestamps in the uploaded photos (common for forwarded images).")
    problems = []
    for p in dated:
        taken = datetime.fromisoformat(p["taken_at"]).date()
        if incident and (incident - taken).days > 2:
            problems.append(f"'{p['name']}' was taken on {taken.isoformat()}, {(incident - taken).days} days before the reported incident")
        elif policy_start and taken < policy_start:
            problems.append(f"'{p['name']}' was taken on {taken.isoformat()}, before the policy started")
    if problems:
        return _signal("photo_metadata", "Photo taken before the incident", "flag", "high", 30, "; ".join(problems) + ".",
                       {"photos": dated})
    return _signal("photo_metadata", "Photo dates match the incident", "pass", "none", 0,
                   f"{len(dated)} photo(s) carry capture dates consistent with the incident.", {"photos": dated})


def check_policy_timing(policy_start: date | None, incident: date | None) -> dict:
    if not policy_start or not incident:
        return _signal("policy_timing", "Policy timing not checked", "info", "none", 0, "Incident date unknown.")
    days = (incident - policy_start).days
    if days < 0:
        return _signal("policy_timing", "Incident before policy start", "flag", "high", 40,
                       f"Incident on {incident} is {abs(days)} days before cover began on {policy_start}.", {"days": days})
    if days <= 15:
        return _signal("policy_timing", "Claim very soon after policy purchase", "flag", "high", 25,
                       f"Incident occurred {days} day(s) after the policy started ({policy_start}).", {"days": days})
    if days <= 45:
        return _signal("policy_timing", "Claim soon after policy purchase", "flag", "medium", 10,
                       f"Incident occurred {days} days after the policy started.", {"days": days})
    return _signal("policy_timing", "Policy in force for a normal period", "pass", "none", 0,
                   f"Policy had been active for {days} days at the time of the incident.", {"days": days})


def check_bill_arithmetic(bills: list[dict]) -> dict:
    if not bills:
        return _signal("bill_math", "No bills to verify", "info", "none", 0, "No repair bill or estimate was uploaded.")
    issues = []
    for b in bills:
        items_sum = round(sum(float(li.get("amount", 0) or 0) for li in b.get("line_items", [])), 2)
        subtotal = float(b.get("subtotal") or 0)
        tax = float(b.get("tax") or 0)
        total = float(b.get("total") or 0)
        name = b.get("bill_number") or f"file {b.get('file_index')}"
        if subtotal and abs(items_sum - subtotal) > 2:
            issues.append(f"Bill {name}: line items add up to ₹{items_sum:,.0f} but subtotal shows ₹{subtotal:,.0f}")
        base = subtotal or items_sum
        if total and abs(base + tax - total) > 2:
            issues.append(f"Bill {name}: subtotal ₹{base:,.0f} + tax ₹{tax:,.0f} = ₹{base + tax:,.0f}, but total shows ₹{total:,.0f} (difference ₹{total - base - tax:,.0f})")
    if issues:
        return _signal("bill_math", "Bill totals don't add up", "flag", "high", 30, "; ".join(issues) + ".", {"issues": issues})
    return _signal("bill_math", "Bill arithmetic verified", "pass", "none", 0,
                   f"Line items, tax and totals reconcile on {len(bills)} bill(s).")


def check_bill_dates(bills: list[dict], incident: date | None) -> dict:
    if not bills or not incident:
        return _signal("bill_dates", "Bill dates not checked", "info", "none", 0, "No bill or incident date.")
    early = []
    for b in bills:
        d = _parse_date(b.get("bill_date"))
        if d and d < incident:
            early.append(f"{b.get('kind', 'bill')} {b.get('bill_number', '')} is dated {d}, {(incident - d).days} day(s) before the incident")
    if early:
        return _signal("bill_dates", "Bill dated before the incident", "flag", "high", 25, "; ".join(early) + ".")
    return _signal("bill_dates", "Bill dates are after the incident", "pass", "none", 0, "All bills are dated on or after the incident.")


def check_claim_history(claimant_claims_12m: int) -> dict:
    if claimant_claims_12m >= 2:
        return _signal("claim_history", "Frequent claimant", "flag", "medium", 15,
                       f"{claimant_claims_12m} claims in the last 12 months on this policyholder's record.")
    return _signal("claim_history", "Normal claim history", "pass", "none", 0,
                   f"{claimant_claims_12m} prior claim(s) in the last 12 months.")


def check_amount_vs_idv(claimed: float, idv: float) -> dict:
    if not claimed or not idv:
        return _signal("amount_vs_idv", "Claim size not compared", "info", "none", 0, "Claimed amount unknown.")
    ratio = claimed / idv
    if ratio >= 0.75:
        return _signal("amount_vs_idv", "Claim close to total loss", "flag", "medium", 10,
                       f"Claimed ₹{claimed:,.0f} is {ratio:.0%} of the insured value (IDV ₹{idv:,.0f}).")
    return _signal("amount_vs_idv", "Claim size is proportionate", "pass", "none", 0,
                   f"Claimed ₹{claimed:,.0f} is {ratio:.1%} of IDV ₹{idv:,.0f}.")


def check_reporting_delay(incident: date | None, reported: date) -> dict:
    if not incident:
        return _signal("reporting_delay", "Reporting delay unknown", "info", "none", 0, "Incident date unknown.")
    days = (reported - incident).days
    if days > 7:
        return _signal("reporting_delay", "Late intimation", "flag", "low", 5, f"Reported {days} days after the incident (policy asks for immediate notice).")
    return _signal("reporting_delay", "Reported promptly", "pass", "none", 0, f"Reported {days} day(s) after the incident.")


def run_all_checks(*, photo_hashes, photo_meta, history, policy, intake, claimant_claims_12m, reported_on: date) -> dict:
    incident = _parse_date(intake.get("incident_date"))
    policy_start = _parse_date(policy.get("start_date"))
    bills = intake.get("bills", []) or []
    signals = [
        check_duplicate_photos(photo_hashes, history),
        check_photo_dates(photo_meta, incident, policy_start),
        check_policy_timing(policy_start, incident),
        check_bill_arithmetic(bills),
        check_bill_dates(bills, incident),
        check_claim_history(claimant_claims_12m),
        check_amount_vs_idv(float(intake.get("claimed_amount_inr") or 0), float(policy.get("idv") or 0)),
        check_reporting_delay(incident, reported_on),
    ]
    rule_score = min(100, sum(s["weight"] for s in signals if s["status"] == "flag"))
    return {
        "signals": signals,
        "rule_score": rule_score,
        "flags": sum(1 for s in signals if s["status"] == "flag"),
        "checked": len(signals),
    }
