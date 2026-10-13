"""Structured outputs for every LLM agent in the pipeline.

These pydantic models are passed to ADK as `output_schema`, so Gemini is forced
to answer in exactly this shape (controlled generation). Fields deliberately
have no defaults and use simple types so the schema converts cleanly for both
the Gemini API and Vertex AI.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Intake agent
# ---------------------------------------------------------------------------

DocType = Literal[
    "damage_photo",
    "repair_bill",
    "repair_estimate",
    "police_report",
    "driving_licence",
    "registration_certificate",
    "other",
]


class DocumentInfo(BaseModel):
    file_index: int = Field(description="The FILE number from the claim message.")
    file_name: str
    doc_type: DocType
    summary: str = Field(description="One sentence on what this file shows.")


class BillLine(BaseModel):
    description: str
    amount: float = Field(description="Line amount in INR, as printed.")


class Bill(BaseModel):
    file_index: int
    vendor: str
    bill_number: str
    bill_date: str = Field(description="As printed, normalised to YYYY-MM-DD if possible.")
    kind: Literal["invoice", "estimate"]
    for_vehicle: bool = Field(description="True if this bill is for repairing the insured vehicle; false for anything else (e.g. a phone).")
    line_items: list[BillLine]
    subtotal: float = Field(description="Subtotal printed on the bill (0 if not printed).")
    tax: float = Field(description="Total tax printed on the bill (0 if not printed).")
    total: float = Field(description="Grand total printed on the bill.")


class IntakeResult(BaseModel):
    language: str = Field(description="Language the claimant used, e.g. Telugu, Hindi, English.")
    language_code: str = Field(description="ISO 639-1 code, e.g. te, hi, en.")
    statement_english: str = Field(description="Faithful English translation of the claimant's account.")
    incident_date: str = Field(description="YYYY-MM-DD. Resolve relative dates using the report date. 'unknown' if not stated.")
    incident_time: str = Field(description="HH:MM 24h, or 'unknown'.")
    incident_location: str
    incident_type: Literal["collision", "theft", "flood", "fire", "vandalism", "other"]
    incident_summary: str = Field(description="Two neutral sentences describing what happened.")
    vehicle_registration: str
    vehicle_make_model: str
    third_party_involved: bool
    injuries_reported: bool
    police_report_mentioned: bool
    documents: list[DocumentInfo]
    bills: list[Bill]
    claimed_amount_inr: float = Field(description="Total amount the claimant is asking for (largest bill total, or amount stated). 0 if unknown.")
    non_vehicle_items_claimed: list[str] = Field(description="Personal belongings or non-vehicle items the claimant mentions as damaged, e.g. 'mobile phone'.")
    missing_information: list[str]


# ---------------------------------------------------------------------------
# Coverage agent
# ---------------------------------------------------------------------------


class CoverageItem(BaseModel):
    item: str = Field(description="What is being claimed, e.g. 'Rear bumper repair', 'Mobile phone'.")
    status: Literal["covered", "excluded", "limited"]
    reason: str
    clause_ref: str = Field(description="Section/clause number from the policy wording, e.g. 'Sec I.1' or 'Exclusion 4(b)'.")
    clause_quote: str = Field(description="Short verbatim quote (max 30 words) from the policy that supports this.")


class CoverageResult(BaseModel):
    policy_active_on_incident_date: bool
    verdict: Literal["covered", "partially_covered", "not_covered", "needs_review"]
    items: list[CoverageItem]
    depreciation_applies: bool = Field(description="False only if a Zero Depreciation add-on is in force.")
    compulsory_deductible_inr: float
    conditions_to_verify: list[str]
    summary: str


# ---------------------------------------------------------------------------
# Damage agent
# ---------------------------------------------------------------------------

PartCode = Literal[
    "front_bumper", "rear_bumper", "bonnet", "boot_lid", "grille", "radiator",
    "headlamp_left", "headlamp_right", "tail_lamp_left", "tail_lamp_right",
    "fender_left", "fender_right", "quarter_panel_left", "quarter_panel_right",
    "door_front_left", "door_front_right", "door_rear_left", "door_rear_right",
    "side_mirror_left", "side_mirror_right", "windshield", "rear_windshield",
    "door_glass", "roof", "alloy_wheel", "tyre", "number_plate", "other",
]


class PhotoFinding(BaseModel):
    file_index: int
    view: str = Field(description="Camera view, e.g. 'rear', 'rear-left', 'front close-up'.")
    quality: Literal["good", "blurry", "dark", "partial", "not_a_vehicle"]
    notes: str


class DamagedPart(BaseModel):
    part_code: PartCode
    part_name: str
    file_index: int = Field(description="Photo in which the damage is most visible.")
    box_2d: list[int] = Field(description="[ymin, xmin, ymax, xmax] of the damaged area, normalised to 0-1000.")
    severity: Literal["minor", "moderate", "severe"]
    action: Literal["repair", "replace"]
    confidence: float = Field(description="0.0 - 1.0")
    observation: str = Field(description="What you see, e.g. 'bumper cracked at left corner, paint transfer'.")


class DamageResult(BaseModel):
    photos: list[PhotoFinding]
    damaged_parts: list[DamagedPart]
    impact_direction: Literal["front", "rear", "left", "right", "multiple", "unclear"]
    consistent_with_statement: bool
    consistency_notes: str
    possible_pre_existing_damage: list[str]
    summary: str


# ---------------------------------------------------------------------------
# Fraud analyst agent
# ---------------------------------------------------------------------------


class RedFlag(BaseModel):
    title: str
    severity: Literal["low", "medium", "high"]
    evidence: str
    source: Literal["photo_forensics", "document_forensics", "policy_timing", "claim_history", "statement", "billing"]


class FraudResult(BaseModel):
    risk_score: int = Field(description="0 (clean) to 100 (almost certainly fraudulent).")
    risk_level: Literal["low", "medium", "high"]
    red_flags: list[RedFlag]
    document_tampering_suspected: bool
    recommended_checks: list[str]
    summary: str


# ---------------------------------------------------------------------------
# Adjudicator agent
# ---------------------------------------------------------------------------


class Reason(BaseModel):
    point: str
    source: Literal["intake", "coverage", "damage", "fraud", "estimate", "policy"]
    impact: Literal["supports", "against", "neutral"]


class DecisionBrief(BaseModel):
    recommendation: Literal["approve", "approve_partial", "investigate", "request_info", "reject"]
    recommended_payout_inr: float
    confidence: int = Field(description="0-100: how sure you are that a careful human adjuster would agree.")
    headline: str = Field(description="One line for the adjuster, max 18 words.")
    rationale: list[Reason]
    next_steps: list[str]
    fast_track_eligible: bool
    customer_language: str
    customer_message_english: str = Field(description="Warm, plain message to the claimant. Never mention fraud or suspicion.")
    customer_message_local: str = Field(description="The same message in the claimant's own language and script.")
