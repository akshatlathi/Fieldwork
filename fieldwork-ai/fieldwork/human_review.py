"""Persistent human-review queue. Inspection suggests; only a person settles issues."""
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Literal
import uuid

from pydantic import BaseModel, Field, ConfigDict
from . import config, escrow
from .spec import ConditionRecord
from .store import store
from .unbox.gate import UnboxResult

_lock = RLock()


@contextmanager
def transaction():
    # Serializes payment/issue writes in the local single-process prototype.
    with _lock:
        yield


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Decision(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    action: Literal["release", "refund", "request_evidence"]
    refund_pct: int = Field(default=0, ge=0, le=100)
    reviewer: str = Field(min_length=1, max_length=120)
    note: str = Field(min_length=1, max_length=2000)


class IssueReport(BaseModel):
    id: str
    item_id: str
    mandate_id: str | None = None
    created_at: str
    updated_at: str
    status: Literal["processing", "awaiting_review", "needs_evidence", "resolved"] = "processing"
    buyer_text: str = ""
    listing: dict
    amount: int | None = None
    currency: str
    suggested_assessment: Literal["consistent", "differs", "cant_tell"] = "cant_tell"
    summary: str = "Inspection is pending. A person will decide the outcome."
    limitations: list[str] = Field(default_factory=list)
    inspection: dict | None = None
    media: list[dict] = Field(default_factory=list)
    history: list[dict] = Field(default_factory=list)
    decision: dict | None = None
    inspection_models: dict = Field(default_factory=lambda: {
        "matching": "google/siglip2-base-patch16-224", "changes": config.DINO_MODEL,
        "crop_judge_requested": config.MODEL_FLASH,
    })


def get(issue_id: str) -> IssueReport:
    raw = store.get_json("issues", issue_id)
    if raw is None:
        raise KeyError("Unknown issue")
    return IssueReport(**raw)


def save(report: IssueReport) -> IssueReport:
    report.updated_at = now()
    store.put_json("issues", report.id, report.model_dump(mode="json"))
    return report


def list_reports(item_id: str | None = None) -> list[IssueReport]:
    reports = [IssueReport(**r) for r in store.list_json("issues")]
    return sorted((r for r in reports if item_id is None or r.item_id == item_id),
                  key=lambda r: r.created_at, reverse=True)


def has_open_issue(item_id: str) -> bool:
    return any(r.status != "resolved" for r in list_reports(item_id))


def begin(record: ConditionRecord, buyer_text: str, mandate_id: str | None) -> IssueReport:
    with transaction():
        if has_open_issue(record.id):
            raise ValueError("An issue is already open for this item. Open its report to add evidence.")
        mandates = [m for m in store.list_json("mandates") if m["item_id"] == record.id and m["status"] == "held"]
        if not mandate_id and len(mandates) == 1:
            mandate_id = mandates[0]["id"]
        if not mandate_id and len(mandates) > 1:
            raise ValueError("Choose the escrow associated with this purchase.")
        mandate = None
        if mandate_id:
            raw = store.get_json("mandates", mandate_id)
            if raw is None or raw["item_id"] != record.id:
                raise ValueError("Escrow does not belong to this item.")
            mandate = escrow.get(mandate_id)
            if mandate.status != "held":
                raise ValueError("This escrow has already been settled.")
        return save(IssueReport(
            id="issue_" + uuid.uuid4().hex[:12], item_id=record.id, mandate_id=mandate_id,
            created_at=now(), updated_at=now(), buyer_text=buyer_text.strip(),
            listing=record.public().model_dump(mode="json"),
            amount=mandate.amount if mandate else None,
            currency=mandate.currency if mandate else record.currency,
            media=[{"label": f"Listing {fid}", "url": store.media_url(record.id, f"{fid}.jpg")}
                   for fid in record.capture.frames],
        ))


def _public_inspection(report: IssueReport, inspection: UnboxResult) -> dict:
    data = asdict(inspection)
    base = store.item_dir(report.item_id).resolve()
    for finding in data["findings"] + data.get("comparisons", []):
        for key in ("listing_crop", "unbox_crop"):
            if finding.get(key):
                try:
                    rel = Path(finding[key]).resolve().relative_to(base).as_posix()
                    finding[key] = store.media_url(report.item_id, rel)
                except ValueError:
                    finding[key] = None
    return data


def complete(issue_id: str, inspection: UnboxResult | None, failure: str | None = None) -> IssueReport:
    with transaction():
        report = get(issue_id)
        report.status = "awaiting_review"
        report.limitations = ["The comparison does not establish smell, feel, fit, or physical item identity.",
                               "Candidate thresholds have only preliminary synthetic validation."]
        if inspection is None:
            report.inspection = None
            report.suggested_assessment = "cant_tell"
            report.summary = "Inspection could not be completed. Review the supplied media and buyer statement."
            report.limitations.append(failure or "Inspection unavailable.")
        else:
            report.inspection = _public_inspection(report, inspection)
            report.suggested_assessment = inspection.verdict
            report.summary = {
                "consistent": "No qualifying difference was detected in the compared views. The buyer's issue still needs human review.",
                "differs": "The inspection found a possible condition difference. A person must review the evidence.",
                "cant_tell": "The comparison is inconclusive. A person must review the evidence and may request a close-up.",
            }[inspection.verdict]
            report.limitations.extend(inspection.limitations)
            report.limitations.extend(inspection.flags)
            report.limitations.append(f"{inspection.pairs_aligned} of {len(report.listing['capture']['frames'])} listing views aligned; this is not full garment coverage.")
        report.history.append({"at": now(), "event": "inspection_completed", "assessment": report.suggested_assessment})
        return save(report)


def review(issue_id: str, decision: Decision) -> IssueReport:
    with transaction():
        report = get(issue_id)
        if report.status == "resolved":
            raise ValueError("This issue has already been resolved.")
        if report.status == "processing":
            raise ValueError("Inspection is still processing.")
        if decision.action == "refund" and decision.refund_pct == 0:
            raise ValueError("Choose a refund percentage greater than zero.")
        if decision.action != "refund" and decision.refund_pct != 0:
            raise ValueError("Refund percentage only applies to a refund decision.")
        entry = {**decision.model_dump(), "at": now()}
        if decision.action == "request_evidence":
            report.status = "needs_evidence"
        else:
            if report.mandate_id:
                if escrow.get(report.mandate_id).status != "held":
                    raise ValueError("The attached escrow has already been settled.")
                escrow.settle(report.mandate_id, "human_review", decision.refund_pct, by=decision.reviewer)
            report.status = "resolved"
        report.decision = entry
        report.history.append({"event": "human_review", **entry})
        return save(report)
