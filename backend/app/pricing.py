"""Deterministic repair-cost and payout engine.

The LLM identifies *which* parts are damaged and whether they need repair or
replacement. The money maths is done here, in plain code, so every rupee in the
brief is reproducible and auditable.

Prices are indicative 2026 Indian market figures for demo purposes (genuine
parts, authorised workshop, ex-GST). Depreciation follows the standard
IRDAI motor tariff schedule (simplified).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

GST_RATE = 0.18

# material: drives depreciation. metal -> age-based, plastic/rubber -> 50%,
# fibre -> 30%, glass -> nil.
# price: replacement part cost per segment (hatchback, sedan, suv)
# labour: (repair labour, replace/fit labour)
# paint: painting charge for the panel, 0 if the part is not painted.
CATALOG: dict[str, dict] = {
    "front_bumper":       {"name": "Front bumper",            "material": "plastic", "price": (6500, 9800, 14500),  "labour": (1800, 1200), "paint": 4200},
    "rear_bumper":        {"name": "Rear bumper",             "material": "plastic", "price": (6200, 9200, 13800),  "labour": (1800, 1200), "paint": 4200},
    "bonnet":             {"name": "Bonnet",                  "material": "metal",   "price": (9800, 14500, 21000), "labour": (2600, 1500), "paint": 5200},
    "boot_lid":           {"name": "Boot lid / tailgate",     "material": "metal",   "price": (11200, 15800, 24500),"labour": (2600, 1500), "paint": 5000},
    "grille":             {"name": "Front grille",            "material": "plastic", "price": (2400, 3900, 6800),   "labour": (0, 600),     "paint": 0},
    "radiator":           {"name": "Radiator",                "material": "metal",   "price": (7800, 10500, 14800), "labour": (0, 1800),    "paint": 0},
    "headlamp_left":      {"name": "Headlamp (left)",         "material": "plastic", "price": (6800, 11500, 18500), "labour": (0, 900),     "paint": 0},
    "headlamp_right":     {"name": "Headlamp (right)",        "material": "plastic", "price": (6800, 11500, 18500), "labour": (0, 900),     "paint": 0},
    "tail_lamp_left":     {"name": "Tail lamp (left)",        "material": "plastic", "price": (3400, 5600, 8900),   "labour": (0, 600),     "paint": 0},
    "tail_lamp_right":    {"name": "Tail lamp (right)",       "material": "plastic", "price": (3400, 5600, 8900),   "labour": (0, 600),     "paint": 0},
    "fender_left":        {"name": "Front fender (left)",     "material": "metal",   "price": (3800, 5600, 8200),   "labour": (1900, 1200), "paint": 3800},
    "fender_right":       {"name": "Front fender (right)",    "material": "metal",   "price": (3800, 5600, 8200),   "labour": (1900, 1200), "paint": 3800},
    "quarter_panel_left": {"name": "Rear quarter panel (left)","material": "metal",  "price": (12500, 16800, 22500),"labour": (3200, 4500), "paint": 4400},
    "quarter_panel_right":{"name": "Rear quarter panel (right)","material": "metal", "price": (12500, 16800, 22500),"labour": (3200, 4500), "paint": 4400},
    "door_front_left":    {"name": "Front door (left)",       "material": "metal",   "price": (14500, 19800, 27500),"labour": (2400, 1800), "paint": 4600},
    "door_front_right":   {"name": "Front door (right)",      "material": "metal",   "price": (14500, 19800, 27500),"labour": (2400, 1800), "paint": 4600},
    "door_rear_left":     {"name": "Rear door (left)",        "material": "metal",   "price": (13800, 18900, 26000),"labour": (2400, 1800), "paint": 4600},
    "door_rear_right":    {"name": "Rear door (right)",       "material": "metal",   "price": (13800, 18900, 26000),"labour": (2400, 1800), "paint": 4600},
    "side_mirror_left":   {"name": "Side mirror (left)",      "material": "plastic", "price": (2900, 4600, 7400),   "labour": (0, 500),     "paint": 900},
    "side_mirror_right":  {"name": "Side mirror (right)",     "material": "plastic", "price": (2900, 4600, 7400),   "labour": (0, 500),     "paint": 900},
    "windshield":         {"name": "Windshield",              "material": "glass",   "price": (7200, 11800, 16500), "labour": (0, 1500),    "paint": 0},
    "rear_windshield":    {"name": "Rear windshield",         "material": "glass",   "price": (5600, 8900, 12800),  "labour": (0, 1400),    "paint": 0},
    "door_glass":         {"name": "Door glass",              "material": "glass",   "price": (2600, 3800, 5200),   "labour": (0, 700),     "paint": 0},
    "roof":               {"name": "Roof panel",              "material": "metal",   "price": (18500, 24500, 32000),"labour": (4200, 6500), "paint": 6200},
    "alloy_wheel":        {"name": "Alloy wheel",             "material": "metal",   "price": (7200, 9800, 14500),  "labour": (900, 400),   "paint": 0},
    "tyre":               {"name": "Tyre",                    "material": "rubber",  "price": (4600, 6800, 9800),   "labour": (0, 300),     "paint": 0},
    "number_plate":       {"name": "Number plate (HSRP)",     "material": "metal",   "price": (900, 900, 900),      "labour": (0, 200),     "paint": 0},
    "other":              {"name": "Other part",              "material": "metal",   "price": (3000, 4500, 6500),   "labour": (1200, 800),  "paint": 1500},
}

SEGMENT_INDEX = {"hatchback": 0, "sedan": 1, "suv": 2}

SEVERITY_LABOUR_FACTOR = {"minor": 0.6, "moderate": 1.0, "severe": 1.5}

# Paint material is treated as 25% of the painting charge; 50% depreciation
# applies only to that material share.
PAINT_MATERIAL_SHARE = 0.25


def metal_depreciation_pct(vehicle_age_months: int) -> float:
    """IRDAI schedule for metal parts by vehicle age."""
    m = vehicle_age_months
    if m <= 6:
        return 0.0
    if m <= 12:
        return 5.0
    if m <= 24:
        return 10.0
    if m <= 36:
        return 15.0
    if m <= 48:
        return 25.0
    if m <= 60:
        return 35.0
    if m <= 120:
        return 40.0
    return 50.0


def depreciation_pct(material: str, vehicle_age_months: int) -> float:
    if material in {"plastic", "rubber"}:
        return 50.0
    if material == "fibre":
        return 30.0
    if material == "glass":
        return 0.0
    return metal_depreciation_pct(vehicle_age_months)


def compulsory_deductible(cubic_capacity: int) -> int:
    """Compulsory deductible for private cars (IMT standard)."""
    return 1000 if cubic_capacity <= 1500 else 2000


def months_between(start: date, end: date) -> int:
    return max(0, (end.year - start.year) * 12 + (end.month - start.month) - (1 if end.day < start.day else 0))


@dataclass
class EstimateLine:
    part_code: str
    part_name: str
    action: str
    severity: str
    material: str
    parts_cost: float
    labour_cost: float
    paint_cost: float
    gross: float
    depreciation_pct: float
    depreciation_amount: float
    payable: float
    excluded: bool
    note: str

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def _round(x: float) -> float:
    return float(round(x))


def estimate_claim(
    damaged_parts: list[dict],
    *,
    segment: str,
    vehicle_age_months: int,
    zero_dep: bool,
    deductible: float,
    claimed_amount: float,
    excluded_part_codes: set[str] | None = None,
) -> dict:
    """Build a line-by-line estimate and a recommended payout."""
    seg = SEGMENT_INDEX.get(segment, 0)
    excluded_part_codes = excluded_part_codes or set()
    lines: list[EstimateLine] = []
    seen: set[str] = set()

    for part in damaged_parts:
        code = part.get("part_code", "other")
        if code in seen and code != "other":
            continue  # same part seen in two photos
        seen.add(code)
        cat = CATALOG.get(code, CATALOG["other"])
        action = part.get("action", "repair")
        severity = part.get("severity", "moderate")
        material = cat["material"]
        repair_labour, replace_labour = cat["labour"]

        if action == "replace" or repair_labour == 0:
            action = "replace"
            parts_cost = cat["price"][seg]
            labour = replace_labour
        else:
            parts_cost = 0.0
            labour = repair_labour * SEVERITY_LABOUR_FACTOR.get(severity, 1.0)
        paint = cat["paint"] * (1.0 if action == "replace" else SEVERITY_LABOUR_FACTOR.get(severity, 1.0) * 0.8)

        parts_cost = parts_cost * (1 + GST_RATE)
        labour = labour * (1 + GST_RATE)
        paint = paint * (1 + GST_RATE)
        gross = parts_cost + labour + paint

        dep_pct = 0.0 if zero_dep else depreciation_pct(material, vehicle_age_months)
        paint_dep = 0.0 if zero_dep else paint * PAINT_MATERIAL_SHARE * 0.5
        dep_amount = parts_cost * dep_pct / 100.0 + paint_dep
        excluded = code in excluded_part_codes
        payable = 0.0 if excluded else gross - dep_amount

        note_bits = []
        if zero_dep:
            note_bits.append("Zero-dep add-on: no depreciation")
        elif dep_pct:
            note_bits.append(f"{dep_pct:g}% depreciation on {material} part")
        if paint_dep:
            note_bits.append("50% on paint material")
        if excluded:
            note_bits.append("Excluded under policy")

        lines.append(
            EstimateLine(
                part_code=code,
                part_name=part.get("part_name") or cat["name"],
                action=action,
                severity=severity,
                material=material,
                parts_cost=_round(parts_cost),
                labour_cost=_round(labour),
                paint_cost=_round(paint),
                gross=_round(gross),
                depreciation_pct=dep_pct,
                depreciation_amount=_round(dep_amount),
                payable=_round(payable),
                excluded=excluded,
                note="; ".join(note_bits),
            )
        )

    gross_total = sum(l.gross for l in lines)
    dep_total = sum(l.depreciation_amount for l in lines if not l.excluded)
    excluded_total = sum(l.gross for l in lines if l.excluded)
    after_dep = gross_total - dep_total - excluded_total
    assessed = max(0.0, after_dep - deductible) if lines else 0.0

    # Never pay more than the claimant actually billed (less deductible).
    claimed_cap = max(0.0, claimed_amount - deductible) if claimed_amount else None
    recommended = min(assessed, claimed_cap) if claimed_cap is not None else assessed

    variance_pct = None
    if claimed_amount and gross_total:
        variance_pct = round((claimed_amount - gross_total) / gross_total * 100, 1)

    return {
        "lines": [l.as_dict() for l in lines],
        "currency": "INR",
        "gst_rate": GST_RATE,
        "segment": segment,
        "vehicle_age_months": vehicle_age_months,
        "zero_dep": zero_dep,
        "gross_total": _round(gross_total),
        "depreciation_total": _round(dep_total),
        "excluded_total": _round(excluded_total),
        "deductible": _round(deductible),
        "assessed_payable": _round(assessed),
        "claimed_amount": _round(claimed_amount or 0),
        "bill_vs_estimate_variance_pct": variance_pct,
        "recommended_payout": _round(recommended),
        "capped_by_bill": claimed_cap is not None and claimed_cap < assessed,
    }
