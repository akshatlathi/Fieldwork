"""Fieldwork Condition Spec v0: the garment's evidence record.

One record per listed garment. Everything (Garment Pass, Ask the garment, the buyer
agent, the unbox check, cases) reads this. Claims are *coded* (language-neutral) and
rendered into any language at read time, which keeps the record small for agents.

Four lanes, so nobody mistakes a seller's word for evidence:
  shown      - visible in the take (has evidence frames + boxes)
  measured   - a number we computed (e.g. chest width), with an error
  declared   - the seller said so; not checkable from the take
  cant_judge - photos/video can't establish it (smell, feel, fit on body)
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class Lane(str, Enum):
    shown = "shown"
    measured = "measured"
    declared = "declared"
    cant_judge = "cant_judge"


class Severity(str, Enum):
    none = "none"
    minor = "minor"
    major = "major"


# Defect codes (language-neutral). Rendered via LABELS below.
DEFECT_CODES = ["stain", "hole", "tear", "pilling", "fading", "snag", "loose_seam", "missing_button", "broken_zip", "discolour", "other"]
# Garment regions (wearer's left/right).
REGIONS = ["front", "back", "collar", "left_sleeve", "right_sleeve", "left_cuff", "right_cuff", "left_armpit", "right_armpit",
           "hem", "pocket", "waistband", "zip", "label", "whole"]


class Box(BaseModel):
    """Normalised [0-1000] box on a frame, Gemini's native convention: ymin, xmin, ymax, xmax."""

    frame_id: str
    box_2d: list[int] = Field(min_length=4, max_length=4)


class Claim(BaseModel):
    id: str
    lane: Lane
    code: str  # a DEFECT_CODES entry, or an attribute code such as "no_stain_visible"
    region: str = "whole"
    severity: Severity = Severity.none
    note: str = ""  # short English note; rendering translates it
    evidence: list[Box] = []
    value: float | None = None  # measured lane
    error: float | None = None  # measured lane, same unit


class Item(BaseModel):
    type: str  # e.g. "jacket", "jeans"
    brand: str | None = None
    size_label: str | None = None
    colour: str | None = None
    material: str | None = None  # from the care label if readable


class Capture(BaseModel):
    code_expected: str
    code_seen: bool
    take_sha256: str
    frames: list[str] = []  # frame ids kept as evidence
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ConditionRecord(BaseModel):
    spec: str = "fieldwork.condition/v0"
    id: str
    item: Item
    claims: list[Claim]
    grade_set: list[int] = []  # conformal set from our model, e.g. [3, 4]
    grade_model: str = "fieldwork-siglip2-ordinal-v0"
    price_band: tuple[int, int] | None = None  # legacy compatibility: (seller asking price, same price), never an estimate
    currency: str = "INR"
    capture: Capture
    listing_text_en: str = ""

    def public(self) -> "ConditionRecord":
        """The buyer/agent-facing view: no capture code."""
        r = self.model_copy(deep=True)
        r.capture.code_expected = "hidden"
        return r

    def summary_line(self) -> str:
        shown = [c for c in self.claims if c.lane == Lane.shown and c.severity != Severity.none]
        flaws = ", ".join(f"{c.severity.value} {c.code} ({c.region})" for c in shown) or "no flaws shown"
        g = "–".join(str(x) for x in (self.grade_set[:1] + self.grade_set[-1:])) if self.grade_set else "?"
        return f"{self.item.brand or ''} {self.item.type}, grade {g}/5; {flaws}".strip()


# Merchant Center / schema.org condition mapping for agents (agent-readable export).
def to_schema_org(r: ConditionRecord) -> dict:
    top = max(r.grade_set) if r.grade_set else 3
    return {
        "@type": "Product",
        "name": f"{r.item.brand or ''} {r.item.type}".strip(),
        "itemCondition": "https://schema.org/UsedCondition",
        "additionalProperty": [
            {"@type": "PropertyValue", "name": "fieldworkGradeSet", "value": r.grade_set},
            {"@type": "PropertyValue", "name": "fieldworkSpec", "value": r.spec},
            {"@type": "PropertyValue", "name": "fieldworkTopGrade", "value": top},
        ],
    }
