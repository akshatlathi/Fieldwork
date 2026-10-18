"""Seller drafts, immutable capture attempts and explicit publication.

Local prototype locks serialize updates in one process. Production multi-worker
use requires transactional updates and seller ownership authentication.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import threading
from typing import Literal
import uuid

from pydantic import BaseModel, Field, field_validator, model_validator

from .spec import Claim, ConditionRecord, Lane, Severity, DEFECT_CODES, REGIONS

_locks: dict[str, threading.RLock] = {}
_guard = threading.Lock()


def lock(item_id):
    with _guard:
        return _locks.setdefault(item_id, threading.RLock())


def now():
    return datetime.now(timezone.utc).isoformat()


class Conflict(ValueError):
    pass


class SellerIssue(BaseModel):
    code: str
    region: str = "whole"
    description: str = Field(min_length=1, max_length=500)

    @field_validator("code")
    @classmethod
    def check_code(cls, value):
        if value not in DEFECT_CODES:
            raise ValueError("Choose a supported issue type")
        return value

    @field_validator("region")
    @classmethod
    def check_region(cls, value):
        if value not in REGIONS:
            raise ValueError("Choose a supported garment region")
        return value

    @field_validator("description")
    @classmethod
    def strip_description(cls, value):
        if not value.strip():
            raise ValueError("Describe the issue and its location")
        return value.strip()


class DisclosureIn(BaseModel):
    revision: int = Field(ge=1)
    answer: Literal["issues_reported", "none_known", "unknown"]
    issues: list[SellerIssue] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def coherent(self):
        if self.answer == "issues_reported" and not self.issues:
            raise ValueError("Describe at least one known issue")
        if self.answer != "issues_reported" and self.issues:
            raise ValueError("Select known issues to save disclosures")
        return self


class PublishIn(BaseModel):
    revision: int = Field(ge=1)
    acknowledge_limitations: bool = False


def _sentence(text):
    text = text.strip()
    return text if not text or text[-1] in ".!?。！？" else text + "."


def _load(storage, item_id):
    meta = storage.get_json("seller_drafts", item_id)
    if meta is None:
        raise KeyError(item_id)
    return meta


def _editable(meta, revision):
    if meta["status"] != "draft":
        raise Conflict("This draft is processing or already published.")
    if meta["revision"] != revision:
        raise Conflict("The draft changed. Reload it before saving or publishing.")


def _project(storage, meta):
    attempt = next((a for a in reversed(meta["attempts"]) if a["status"] == "completed"), None)
    if attempt is None:
        raise Conflict("No completed inspection is available yet.")
    record = ConditionRecord(**deepcopy(attempt["record"]))
    current_findings = {(c.code, c.region) for c in record.claims if c.lane == Lane.shown and c.severity != Severity.none}
    for earlier in reversed(meta["attempts"]):
        if earlier is attempt or earlier["status"] != "completed":
            continue
        for raw_claim in earlier["record"]["claims"]:
            claim = Claim(**deepcopy(raw_claim))
            if claim.lane != Lane.shown or claim.severity == Severity.none or (claim.code, claim.region) in current_findings:
                continue
            claim.id = f"prior_{earlier['id']}_{claim.id}"
            claim.note = "Earlier capture: " + claim.note
            record.claims.append(claim)
            current_findings.add((claim.code, claim.region))
            for box in claim.evidence:
                if box.frame_id not in record.capture.frames:
                    record.capture.frames.append(box.frame_id)
    # A visible overview is evidence of a view, not proof of universal absence.
    for claim in record.claims:
        if claim.lane == Lane.shown and claim.severity == Severity.none:
            claim.code = "view_visible"
            claim.note = f"Recorded view of {claim.region.replace('_', ' ')}; small, folded or hidden details may be unclear."
    for i, issue in enumerate(meta.get("issues", [])):
        record.claims.append(Claim(id=f"seller_issue_{i+1}", lane=Lane.declared, code=issue["code"],
            region=issue["region"], severity=Severity.none, note=issue["description"]))
    answer = meta.get("answer")
    if answer in ("none_known", "unknown"):
        record.claims.append(Claim(id="seller_condition", lane=Lane.declared, code="seller_condition",
            note="Seller reports no known issues; this does not establish absence of defects." if answer == "none_known"
            else "Seller is unsure of the garment's condition; further evidence may be needed."))
    listing = deepcopy(attempt["listing"])
    frame_sources = listing.setdefault("frame_sources", {})
    for earlier in meta["attempts"]:
        for fid, label in (earlier.get("listing", {}).get("frame_sources", {})).items():
            if fid in record.capture.frames:
                frame_sources.setdefault(fid, label)
    coverage = listing.get("capture_coverage") or {}
    limitations = ["Assessment is limited to supplied evidence; small or hidden defects may not be visible."]
    for view in coverage.get("views", []):
        if view["status"] != "shown":
            limitations.append(f"{view['region'].replace('_', ' ').capitalize()} view is {view['status'].replace('_', ' ')}.")
    if answer == "unknown":
        limitations.append("Seller is unsure whether additional issues exist.")
    for issue in meta.get("issues", []):
        limitations.append(f"Seller-reported {issue['code'].replace('_', ' ')} on {issue['region'].replace('_', ' ')}: {_sentence(issue['description'])} Visual confirmation is not established by this disclosure.")
    shown = [c for c in record.claims if c.lane == Lane.shown and c.severity != Severity.none]
    sentences = [f"Second-hand {record.item.type}. Condition assessment is limited to the supplied views."]
    if shown:
        sentences.append("Visible findings: " + "; ".join(f"{c.code.replace('_', ' ')} on {c.region.replace('_', ' ')}" for c in shown) + ".")
    else:
        sentences.append("No visible defect was identified in these views; this does not rule out hidden defects.")
    for issue in meta.get("issues", []):
        sentences.append(f"Seller reports {issue['code'].replace('_', ' ')} on {issue['region'].replace('_', ' ')}: {_sentence(issue['description'])}")
    if answer == "unknown":
        sentences.append("The seller is unsure about additional issues.")
    record.listing_text_en = " ".join(sentences)
    listing.update(en=record.listing_text_en, publication_status=meta["status"],
                   seller_limitations=limitations, seller_disclosures=deepcopy(meta.get("issues", [])))
    price = meta.get("asking_price")
    record.price_band = (price, price) if price else None  # legacy field; never a condition-based estimate
    record.currency = "INR"
    listing.update(asking_price=price, currency="INR", price_source="seller" if price else "unset",
                   negotiation_enabled=meta.get("negotiation_enabled", False))
    guidance = list(coverage.get("guidance", []))
    for issue in meta.get("issues", []):
        guidance.append(f"Unfold the {issue['region'].replace('_', ' ')} area and add a close-up plus a wider context view of the reported {issue['code'].replace('_', ' ')}.")
    return record, listing, limitations, guidance


def _save_projection(storage, meta):
    from .take.pipeline import translate
    record, listing, _, _ = _project(storage, meta)
    # Rebuild translations from the qualified text, never reuse earlier clean prose.
    for key in ("ja", "ko", "zh-TW", "th", "id-ID", "vi", "hi"):
        listing.pop(key, None)
    previous = storage.get_json("listings", meta["id"]) or {}
    if previous.get("en") == record.listing_text_en and any(previous.get(k) for k in ("ja", "hi")):
        listing.update({k: previous[k] for k in ("ja", "ko", "zh-TW", "th", "id-ID", "vi", "hi") if k in previous})
    else:
        try:
            listing.update(translate(record.listing_text_en))
        except Exception:
            # Losing translation must not lose a seller's disclosure or revive stale text.
            listing["translation_unavailable"] = True
    storage.put_json("records", meta["id"], record.model_dump(mode="json"))
    storage.put_json("listings", meta["id"], listing)


def review(storage, item_id):
    with lock(item_id):
        meta = _load(storage, item_id)
        record, _, limitations, guidance = _project(storage, meta)
        return {"id": item_id, "status": meta["status"], "revision": meta["revision"],
            "asking_price": meta.get("asking_price"), "currency": "INR", "negotiation_enabled": meta.get("negotiation_enabled", False),
            "answer": meta.get("answer"), "issues": meta.get("issues", []),
            "record": record.public().model_dump(mode="json"), "limitations": limitations,
            "guidance": guidance, "history": deepcopy(meta["history"]),
            "attempts": [{"id": a["id"], "status": a["status"], "created_at": a["created_at"],
                "error": a.get("error"), "media": [{"url": storage.media_url(item_id, s["path"]), "sha256": s["sha256"]} for s in a["sources"]]}
                for a in meta["attempts"]]}


def _inspect(storage, meta, video, photos, code):
    from .take.pipeline import run_take
    attempt_id = "a" + uuid.uuid4().hex[:10]
    previous_sources = {key: deepcopy(meta.get(key)) for key in ("video", "photos", "code")}
    attempt = {"id": attempt_id, "status": "processing", "created_at": now(), "sources": []}
    folder = storage.item_dir(meta["id"]) / "seller_attempts" / attempt_id
    folder.mkdir(parents=True)
    for i, source in enumerate(([video] if video else []) + list(photos or [])):
        target = folder / f"source_{i}{source.suffix.lower()}"
        target.write_bytes(source.read_bytes())
        rel = target.relative_to(storage.item_dir(meta["id"])).as_posix()
        attempt["sources"].append({"path": rel, "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
        if video is not None and i == 0:
            meta["video"] = rel
            meta["code"] = code or meta.get("code")
        else:
            meta["photos"].append(rel)
    meta["status"] = "processing"
    storage.put_json("seller_drafts", meta["id"], meta)
    storage.sync_item(meta["id"])
    try:
        source_video = storage.get_file(meta["id"], meta["video"]) if meta.get("video") else None
        source_photos = [storage.get_file(meta["id"], p) for p in meta["photos"]]
        if any(p is None for p in source_photos) or (meta.get("video") and source_video is None):
            raise ValueError("Earlier source evidence is unavailable")
        result = run_take(source_video, meta.get("code"), photos=source_photos, item_id=meta["id"],
                          attempt_id=attempt_id, translate_listing=False)
        attempt.update(status="completed", record=result.model_dump(mode="json"),
                       listing=storage.get_json("listings", meta["id"]))
    except Exception as exc:
        meta.update(previous_sources)
        attempt.update(status="failed", error=f"Inspection unavailable ({type(exc).__name__}); source evidence is retained.")
        meta["attempts"].append(attempt)
        meta.update(status="draft", revision=meta["revision"]+1)
        meta["history"].append({"event": "inspection_failed", "attempt": attempt_id, "at": now()})
        storage.put_json("seller_drafts", meta["id"], meta)
        if not any(a["status"] == "completed" for a in meta["attempts"]):
            raise
        _save_projection(storage, meta)
        return
    meta["attempts"].append(attempt)
    meta.update(status="draft", revision=meta["revision"]+1)
    meta["history"].append({"event": "evidence_inspected", "attempt": attempt_id, "at": now()})
    storage.put_json("seller_drafts", meta["id"], meta)
    _save_projection(storage, meta)


def create(storage, video, photos, code):
    item_id = "g_" + uuid.uuid4().hex[:10]
    with lock(item_id):
        meta = {"id": item_id, "status": "processing", "revision": 0, "answer": None, "issues": [],
                "attempts": [], "history": [], "video": None, "photos": [], "code": code}
        storage.put_json("seller_drafts", item_id, meta)
        _inspect(storage, meta, video, photos, code)
        return ConditionRecord(**storage.get_json("records", item_id))


def disclose(storage, item_id, body: DisclosureIn):
    with lock(item_id):
        meta = _load(storage, item_id); _editable(meta, body.revision)
        meta.update(answer=body.answer, issues=[i.model_dump() for i in body.issues], revision=meta["revision"]+1)
        meta["history"].append({"event": "seller_disclosure_saved", "at": now(), "answer": body.answer,
                                "issues": deepcopy(meta["issues"])})
        storage.put_json("seller_drafts", item_id, meta)
        _save_projection(storage, meta)
        return review(storage, item_id)


def add_evidence(storage, item_id, revision, video, photos, code):
    with lock(item_id):
        meta = _load(storage, item_id); _editable(meta, revision)
        _inspect(storage, meta, video, photos, code)
        return review(storage, item_id)


def set_price(storage, item_id, body):
    with lock(item_id):
        from .catalog import purchased_items
        if item_id in purchased_items(storage):
            raise Conflict("A purchased garment's price cannot be changed.")
        meta = _load(storage, item_id)
        if meta["status"] not in ("draft", "published") or meta["revision"] != body.revision:
            raise Conflict("The listing changed. Reload it before setting its price.")
        # Published legacy listings can receive their first explicit price.
        if meta["status"] == "published" and meta.get("asking_price"):
            raise Conflict("Published prices cannot be edited in this prototype.")
        storage.put_json("floors", item_id, {"floor": body.minimum_price if body.negotiation_enabled else body.asking_price})
        meta.update(asking_price=body.asking_price, negotiation_enabled=body.negotiation_enabled, revision=meta["revision"]+1)
        meta["history"].append({"event": "seller_price_saved", "at": now(), "asking_price": body.asking_price,
                                "currency": "INR", "negotiation_enabled": body.negotiation_enabled})
        storage.put_json("seller_drafts", item_id, meta)
        _save_projection(storage, meta)
        return review(storage, item_id)


def publish(storage, item_id, body: PublishIn):
    with lock(item_id):
        meta = _load(storage, item_id); _editable(meta, body.revision)
        if meta.get("answer") is None:
            raise Conflict("Answer the seller condition question before publishing.")
        if not meta.get("asking_price"):
            raise Conflict("Set your asking price in INR before publishing.")
        if not body.acknowledge_limitations:
            raise Conflict("Review and acknowledge the visible limitations before publishing.")
        _, listing, limitations, _ = _project(storage, meta)
        meta.update(status="published", revision=meta["revision"]+1)
        meta["history"].append({"event": "seller_approved_publication", "at": now(),
                                "limitations": limitations, "revision": body.revision})
        listing = storage.get_json("listings", item_id)
        listing["publication_status"] = "published"
        storage.put_json("listings", item_id, listing)
        storage.put_json("seller_drafts", item_id, meta)
        return review(storage, item_id)
