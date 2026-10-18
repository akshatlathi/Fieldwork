"""Validate independent real-capture ground truth before model evaluation.

python eval/capture_schema.py --root data/garments
Does not call any models or infer missing ground truth.
"""
import argparse
import json
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Flaw(BaseModel):
    code: str
    region: str
    severity: Literal["minor", "major"]
    description: str = Field(min_length=1)
    visible_in_media: bool


class BuyerQuestion(BaseModel):
    question: str = Field(min_length=1)
    expected_state: Literal["shown", "not_in_take", "cant_judge"]
    reference_answer: str = Field(min_length=1)


class CaptureTruth(BaseModel):
    model_config = ConfigDict(extra="forbid")
    garment_id: str = Field(min_length=1)
    comparison_group: str = Field(min_length=1, description="Same physical garment and deliberate look-alike partners share a group")
    split: Literal["development", "calibration", "test"]
    seller_video: str | None = "take.mp4"
    seller_photos: list[str] = Field(default_factory=list)
    code: str | None = None
    attributes: dict[str, str | None] = Field(default_factory=dict)
    received_video: str | None = "unbox/take.mp4"
    received_photos: list[str] = Field(default_factory=list)
    same_garment: bool | None
    actual_change: bool | None
    expected_assessment: Literal["consistent", "differs", "cant_tell"]
    known_flaws: list[Flaw]
    changes: list[Flaw]
    buyer_questions: list[BuyerQuestion] = Field(min_length=1)
    reference_notes: str = Field(min_length=1)
    reference_reviewers: list[str] = Field(min_length=1)
    synthetic: bool = False

    @model_validator(mode="after")
    def coherent_labels(self):
        if not self.seller_video and len(self.seller_photos) < 3:
            raise ValueError("Supply seller video or at least three seller photos")
        if not self.received_video and not self.received_photos:
            raise ValueError("Supply received video or photos")
        if self.actual_change is True and not self.changes:
            raise ValueError("A physical change needs an independent change annotation")
        if self.actual_change is False and self.changes:
            raise ValueError("Unchanged garment cannot have annotated new changes")
        if self.synthetic:
            raise ValueError("Digitally edited captures belong in a separate stress-test track")
        return self


def validate_capture(folder):
    truth = CaptureTruth.model_validate_json((folder / "truth.json").read_text())
    if (folder / "split.txt").exists() and (folder / "split.txt").read_text().strip() != truth.split:
        raise ValueError("split.txt and truth.json disagree")
    for name in [truth.seller_video, truth.received_video, *truth.seller_photos, *truth.received_photos]:
        if name is None:
            continue
        path = (folder / name).resolve()
        if folder.resolve() not in path.parents or not path.is_file():
            raise ValueError(f"Missing or invalid capture path: {name}")
    return truth


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    args = ap.parse_args()
    paths = sorted(args.root.glob("*/truth.json"))
    if not paths:
        raise SystemExit(f"No labelled real captures in {args.root}; no accuracy evaluation can run")
    groups = {}
    rows = []
    for path in paths:
        truth = validate_capture(path.parent)
        previous = groups.setdefault(truth.comparison_group, truth.split)
        if previous != truth.split:
            raise ValueError(f"Split leakage for comparison group {truth.comparison_group}")
        rows.append({"garment_id": truth.garment_id, "group": truth.comparison_group, "split": truth.split})
    print(json.dumps({"validated": len(rows), "captures": rows}, indent=2))


if __name__ == "__main__":
    main()
