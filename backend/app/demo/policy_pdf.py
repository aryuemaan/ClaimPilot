"""Policy schedule + wording for the fictional insurer used in the demo."""

from __future__ import annotations

import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

INSURER = "Suraksha General Insurance Co. Ltd."
INSURER_NOTE = "Fictional insurer created for the ClaimPilot demo."

# Each clause: (ref, heading, text). The coverage agent cites these refs.
WORDING: list[tuple[str, str, str]] = [
    ("Sec I.1", "Section I - Loss of or damage to the vehicle insured",
     "The Company will indemnify the Insured against loss of or damage to the vehicle insured and its accessories whilst thereon "
     "(a) by fire, explosion, self-ignition or lightning; (b) by burglary, housebreaking or theft; (c) by riot and strike; "
     "(d) by earthquake; (e) by flood, typhoon, hurricane, storm, cyclone or inundation; (f) by accidental external means; "
     "(g) by malicious act; (h) whilst in transit by road, rail, inland waterway, lift, elevator or air; (i) by landslide or rockslide."),
    ("Sec I.2", "Depreciation on parts replaced",
     "In the event of the vehicle being partially damaged and parts being replaced, depreciation shall be deducted as follows: "
     "(a) rubber, nylon and plastic parts, tyres and tubes, batteries and air bags - 50%; (b) fibre glass components - 30%; "
     "(c) all parts made of glass - Nil; (d) painting - 50% depreciation on the cost of paint material only; "
     "(e) metal parts, by age of the vehicle: not exceeding 6 months - Nil; 6 months to 1 year - 5%; 1 to 2 years - 10%; "
     "2 to 3 years - 15%; 3 to 4 years - 25%; 4 to 5 years - 35%; 5 to 10 years - 40%; exceeding 10 years - 50%."),
    ("Sec I.3", "Compulsory deductible",
     "Each claim under Section I is subject to a compulsory deductible of Rs 1,000 for vehicles with cubic capacity up to "
     "1500 cc and Rs 2,000 for vehicles above 1500 cc, in addition to any voluntary deductible shown in the Schedule."),
    ("Excl I.4(a)", "Exclusion - wear and tear",
     "The Company shall not be liable for consequential loss, depreciation, wear and tear, mechanical or electrical "
     "breakdown, failures or breakages."),
    ("Excl I.4(b)", "Exclusion - tyres and tubes",
     "The Company shall not be liable for damage to tyres and tubes unless the vehicle is damaged at the same time, in which "
     "case liability is limited to 50% of the cost of replacement."),
    ("Excl I.4(c)", "Exclusion - intoxication",
     "The Company shall not be liable for any accidental loss or damage suffered whilst the Insured or any person driving "
     "with the knowledge and consent of the Insured is under the influence of intoxicating liquor or drugs."),
    ("Excl I.4(d)", "Exclusion - personal belongings",
     "The Company shall not be liable for loss of or damage to personal belongings, mobile phones, electronic devices, "
     "luggage or any other contents carried in the vehicle."),
    ("Excl I.4(e)", "Exclusion - engine water damage",
     "The Company shall not be liable for damage to the engine or gearbox caused by water ingression or hydrostatic lock, "
     "unless the Engine Protect add-on is shown in the Schedule."),
    ("Excl I.4(f)", "Exclusion - loss before cover",
     "The Company shall not be liable for loss or damage occurring before the commencement of the period of insurance."),
    ("Sec II", "Section II - Liability to third parties",
     "The Company will indemnify the Insured against legal liability for death of or bodily injury to any person and damage "
     "to third-party property arising out of the use of the vehicle, subject to the limits of the Motor Vehicles Act, 1988."),
    ("Gen Excp 1", "General exception - unlicensed driver",
     "The Company shall not be liable for any accident, loss or damage whilst the vehicle is being driven by any person "
     "other than an authorised driver holding a valid driving licence."),
    ("Cond 1", "Condition - notice of claim",
     "Notice shall be given in writing to the Company immediately upon the occurrence of any accidental loss or damage. In "
     "the event of a claim the Insured shall give all such information and assistance as the Company may require."),
    ("Cond 2", "Condition - survey before repair",
     "No repair shall be undertaken without the written consent of the Company, which may require the vehicle to be "
     "inspected or surveyed before repairs are authorised."),
    ("Cond 3", "Condition - settlement",
     "The Company may at its own option repair, reinstate or replace the vehicle or pay in cash the amount of the loss or damage."),
    ("Cond 4", "Condition - fraud",
     "If any claim is in any respect fraudulent, or if any fraudulent means or devices are used by the Insured or anyone "
     "acting on the Insured's behalf to obtain any benefit under this policy, all benefits under this policy shall be forfeited."),
    ("Add-on A1", "Add-on - Zero Depreciation",
     "When shown in the Schedule, claims under Section I are paid without deduction for depreciation on parts replaced "
     "(Sec I.2), for up to two claims in the period of insurance. The compulsory deductible continues to apply."),
    ("Add-on A2", "Add-on - Engine Protect",
     "When shown in the Schedule, covers damage to the engine and gearbox from water ingression, hydrostatic lock or oil leakage."),
]


def wording_text() -> str:
    lines = [f"{INSURER} - Private Car Package Policy wording ({INSURER_NOTE})", ""]
    for ref, heading, text in WORDING:
        lines.append(f"[{ref}] {heading}: {text}")
    return "\n".join(lines)


def search_wording(query: str, limit: int = 3) -> list[dict]:
    """Tiny keyword search used by the copilot's policy lookup tool."""
    terms = [t for t in query.lower().replace("-", " ").split() if len(t) > 2]
    scored = []
    for ref, heading, text in WORDING:
        hay = f"{ref} {heading} {text}".lower()
        score = sum(hay.count(t) for t in terms)
        if score:
            scored.append((score, {"ref": ref, "heading": heading, "text": text}))
    scored.sort(key=lambda x: -x[0])
    return [s[1] for s in scored[:limit]]


def _fmt_date(d: date) -> str:
    return d.strftime("%d %b %Y")


def render_policy_pdf(policy: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title=f"Policy {policy['policy_number']}", author=INSURER)
    ss = getSampleStyleSheet()
    brand = colors.HexColor("#0E5A46")
    h1 = ParagraphStyle("h1", parent=ss["Title"], fontSize=17, textColor=brand, alignment=0, spaceAfter=2)
    small = ParagraphStyle("small", parent=ss["Normal"], fontSize=8, textColor=colors.HexColor("#6B7280"))
    body = ParagraphStyle("body", parent=ss["Normal"], fontSize=9, leading=12.5)
    clause_head = ParagraphStyle("ch", parent=body, fontName="Helvetica-Bold", spaceBefore=6)

    v = policy["vehicle"]
    start = date.fromisoformat(policy["start_date"])
    end = date.fromisoformat(policy["end_date"])
    addons = policy.get("addons") or []
    story = [
        Paragraph(INSURER, h1),
        Paragraph(f"Private Car Package Policy - Certificate of Insurance cum Policy Schedule. {INSURER_NOTE}", small),
        Spacer(1, 8),
    ]
    rows = [
        ["Policy number", policy["policy_number"], "Period of insurance", f"{_fmt_date(start)} 00:00 hrs to {_fmt_date(end)} midnight"],
        ["Insured", policy["holder_name"], "Contact", policy["phone_masked"]],
        ["Address", policy["address_masked"], "Customer since", policy.get("customer_since", "-")],
        ["Registration no.", v["registration"], "Make / model", v["make_model"]],
        ["Year of manufacture", str(v["year"]), "Date of registration", _fmt_date(date.fromisoformat(v["registration_date"]))],
        ["Cubic capacity", f"{v['cc']} cc", "Fuel / seats", f"{v['fuel']} / 5"],
        ["Chassis no.", v["chassis_masked"], "Colour", v["colour"]],
        ["Insured declared value (IDV)", f"Rs {policy['idv']:,}", "No claim bonus", f"{policy['ncb_pct']}%"],
        ["Add-on covers", ", ".join(addons) if addons else "None", "Compulsory deductible", f"Rs {1000 if v['cc'] <= 1500 else 2000:,}"],
        ["Voluntary deductible", "Nil", "Total premium (incl. GST)", f"Rs {policy['premium']:,}"],
    ]
    cell = ParagraphStyle("cell", parent=body, fontSize=8.3, leading=10.5)
    cell_b = ParagraphStyle("cellb", parent=cell, fontName="Helvetica-Bold", textColor=colors.HexColor("#374151"))
    rows = [[Paragraph(str(r[0]), cell_b), Paragraph(str(r[1]), cell), Paragraph(str(r[2]), cell_b), Paragraph(str(r[3]), cell)] for r in rows]
    t = Table(rows, colWidths=[34 * mm, 53 * mm, 34 * mm, 53 * mm])
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 8.5),
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 8.5),
        ("FONT", (2, 0), (2, -1), "Helvetica-Bold", 8.5),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#374151")),
        ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#374151")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5D1")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF4F1")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#EEF4F1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story += [t, Spacer(1, 8)]
    story.append(Paragraph(
        "Limitations as to use: the policy covers use for social, domestic and pleasure purposes and for the insured's business. "
        "Persons or classes of persons entitled to drive: any person holding a valid driving licence. "
        "This schedule must be read with the policy wording that follows.", body))
    story.append(PageBreak())
    story.append(Paragraph("Policy wording", h1))
    for ref, heading, text in WORDING:
        story.append(Paragraph(f"[{ref}] {heading}", clause_head))
        story.append(Paragraph(text, body))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"{INSURER_NOTE} Not a real insurance contract.", small))
    doc.build(story)
    return buf.getvalue()
