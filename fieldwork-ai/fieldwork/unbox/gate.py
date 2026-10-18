"""The unbox check: listing take vs unboxing take -> consistent / differs / cant_tell.

Order of evidence
1. Replay guard: an unbox frame (near-)identical to a listing frame is replayed media.
2. Declared-flaw fingerprints: every flaw the seller showed must still be there; a
   missing flaw suggests a different garment (swap).
3. New change: aligned crop pairs from the diff map, judged by Gemini.
This produces a suggested assessment for the report, never a payment decision.
An inconclusive comparison suggests a random close-up for the human reviewer.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from ..spec import ConditionRecord, Lane, Severity
from .. import config
from ..evidence import valid_box
from . import judge
from .align import align
from .diff import change_regions, crop_pair, comparable_box, InsufficientComparisonArea


# Change scores: planted stains ~6, unchanged re-shoots ~2.6 (tests/test_cv.py). Recalibrate on real pairs.
MIN_CHANGE_SCORE = config.CHANGE_SCORE


@dataclass
class Finding:
    kind: str  # new_defect | flaw_missing | replay
    what: str
    region_box: list[int]
    listing_crop: str | None = None
    unbox_crop: str | None = None
    reason: str = ""
    listing_frame_id: str | None = None
    received_frame_id: str | None = None
    listing_label: str | None = None
    received_label: str | None = None


@dataclass
class UnboxResult:
    verdict: str  # consistent | differs | cant_tell
    findings: list[Finding] = field(default_factory=list)
    closeup_request: str | None = None
    pairs_aligned: int = 0
    pairs_total: int = 0
    flags: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    comparisons: list[dict] = field(default_factory=list)
    policy_version: str = "region-correspondence-v1"


def _near_identical(a: Path, b: Path) -> bool:
    ia = cv2.resize(cv2.imread(str(a), cv2.IMREAD_GRAYSCALE), (256, 256)).astype(np.float32)
    ib = cv2.resize(cv2.imread(str(b), cv2.IMREAD_GRAYSCALE), (256, 256)).astype(np.float32)
    return float(np.mean(np.abs(ia - ib))) < 1.5  # real re-shoots never get this close


def check(record: ConditionRecord, listing_frames: dict[str, Path], pairs: list[tuple[str, Path]], work: Path,
          seed: int | None = None, *, reference_masks: dict[str, np.ndarray] | None = None,
          require_garment_focus: bool = False, received_labels: dict[str, str] | None = None,
          listing_labels: dict[str, str] | None = None) -> UnboxResult:
    """pairs: (listing_frame_id, unbox_frame_path) matched upstream (unbox/pair.py)."""
    work.mkdir(parents=True, exist_ok=True)
    res = UnboxResult(verdict="consistent", pairs_total=len({fid for fid, _ in pairs}))
    aligned: dict[str, Path] = {}
    sources: dict[str, dict] = {}
    masks: dict[str, np.ndarray] = {}
    failed_views: set[str] = set()
    replayed_views: set[str] = set()
    unsure = 0

    for fid, ub in pairs:
        if fid in aligned or fid in replayed_views:
            continue
        ref = listing_frames[fid]
        photo = re.search(r"(?:^|_)p(\d+)$", fid)
        label = f"Seller photo {photo[1]} · {fid}" if photo else f"Listing view {fid}"
        source = {"listing_frame_id": fid, "received_frame_id": ub.name,
                  "listing_label": (listing_labels or {}).get(fid, label),
                  "received_label": (received_labels or {}).get(str(ub), f"Received image {ub.name}")}
        if _near_identical(ref, ub):
            replayed_views.add(fid)
            res.flags.append("replayed_listing_media")
            res.findings.append(Finding("replay", "Near-identical listing and received images", [0, 0, 1000, 1000],
                str(ref), str(ub), "These images are nearly identical after resizing. They do not establish an independent received-garment capture.", **source))
            continue
        focus = (reference_masks or {}).get(fid)
        a = align(ref, ub, reference_mask=focus) if focus is not None else align(ref, ub)
        if a.ok and a.warped_path:
            if require_garment_focus:
                if not getattr(a, "garment_focused", False):
                    res.limitations.append(f"Listing view {fid} has no usable garment outline; background correspondence cannot establish garment correspondence.")
                    failed_views.add(fid)
                    continue
                try:
                    correspondence = judge.correspondence(ref, a.warped_path)
                except Exception:
                    res.limitations.append(f"Region correspondence check unavailable for listing view {fid}; no defect conclusion was drawn.")
                    failed_views.add(fid)
                    continue
                if not correspondence.comparable:
                    failed_views.add(fid)
                    res.comparisons.append({"kind": "unmatched_view", "what": "Views could not be matched",
                        "listing_crop": str(ref), "unbox_crop": str(ub), "unsure": True, "comparable": False,
                        "reason": correspondence.reason, **source})
                    continue
            aligned[fid] = a.warped_path
            sources[fid] = source
            if getattr(a, "method", "akaze") == "sift":
                # Real shared-background controls can pass SIFT on different
                # garments. Keep fallback comparisons provisional for review.
                unsure += 1
                res.limitations.append(f"Fallback alignment in listing view {fid} is provisional; garment-area correspondence needs human review.")
            mask_path = getattr(a, "valid_mask_path", None)
            if mask_path:
                mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
                if mask is None:
                    raise OSError("Aligned coverage mask unavailable")
                masks[fid] = mask
            res.comparisons.append({"kind": "aligned_view", "what": f"Compared view {fid}",
                                    "listing_crop": str(ref), "unbox_crop": str(a.warped_path),
                                    "reason": "Provisional aligned view; this does not establish garment identity.", **source})
        else:
            failed_views.add(fid)
    for fid in sorted(failed_views - aligned.keys() - replayed_views):
        res.limitations.append(f"Could not align listing view {fid} after trying candidate views.")
    res.pairs_aligned = len(aligned)

    # Declared-flaw fingerprints.
    for c in record.claims:
        if c.lane != Lane.shown or c.severity == Severity.none:
            continue
        for b in c.evidence:
            if b.frame_id in aligned and valid_box(b.box_2d):
                mask = masks.get(b.frame_id)
                if mask is not None and not comparable_box(mask, b.box_2d):
                    continue  # include the padded context, not only the inner box
                ca, cb = crop_pair(listing_frames[b.frame_id], aligned[b.frame_id], b.box_2d, out_dir=work / b.frame_id)
                v = judge.flaw_still_there(ca, cb, f"{c.severity.value} {c.code} on {c.region}")
                res.comparisons.append({"kind": "existing_flaw", "what": f"Listed {c.code} on {c.region}",
                                        "listing_crop": str(ca), "unbox_crop": str(cb), **v.model_dump(),
                                        "unsure": v.unsure or not v.comparable, **sources[b.frame_id]})
                if v.unsure or not v.comparable:
                    unsure += 1
                if not v.still_visible and not v.unsure and v.comparable:
                    res.findings.append(Finding("flaw_missing", f"listed {c.code} on {c.region} not found", b.box_2d,
                                                str(ca), str(cb), v.reason, **sources[b.frame_id]))
                break
        else:
            res.limitations.append(f"Listed {c.code} on {c.region} could not be checked.")
            unsure += 1

    # New change between listing and unboxing.
    for fid, warped in aligned.items():
        mask = masks.get(fid)
        try:
            regions = change_regions(listing_frames[fid], warped, top_k=3, **({"valid_mask": mask} if mask is not None else {}))
        except InsufficientComparisonArea:
            unsure += 1
            res.limitations.append(f"Insufficient comparable area after alignment borders in listing view {fid}.")
            continue
        for r in regions:
            if r.score < MIN_CHANGE_SCORE:
                continue  # below the noise floor measured in tests/test_cv.py; don't spend a Gemini call
            if mask is not None and not comparable_box(mask, r.box_2d):
                unsure += 1
                res.limitations.append(f"A candidate crop in listing view {fid} extends outside supported alignment; no defect conclusion was drawn.")
                continue
            ca, cb = crop_pair(listing_frames[fid], warped, r.box_2d, out_dir=work / fid)
            v = judge.compare(ca, cb)
            res.comparisons.append({"kind": "candidate_change", "what": f"Candidate change in {fid}",
                                    "listing_crop": str(ca), "unbox_crop": str(cb), **v.model_dump(),
                                    "unsure": v.unsure or not v.comparable, **sources[fid]})
            if v.unsure or not v.comparable:
                unsure += 1
            elif v.new_defect and v.severity in ("minor", "major"):
                res.findings.append(Finding("new_defect", f"new {v.severity} {v.code}", r.box_2d, str(ca), str(cb), v.reason, **sources[fid]))

    if res.flags or any(f.kind in ("new_defect", "flaw_missing") for f in res.findings):
        res.verdict = "differs" if not res.flags else "cant_tell"
    elif res.pairs_aligned == 0 or unsure > 0:
        res.verdict = "cant_tell"

    if res.pairs_aligned < len(listing_frames):
        res.limitations.append("Not all listing views were compared.")
        if res.verdict == "consistent":
            res.verdict = "cant_tell"
    if unsure:
        res.limitations.append("One or more alignment, listed-flaw or crop checks were inconclusive.")

    if res.verdict == "cant_tell":
        # Random, never announced in advance: a cheater can't prepare for it.
        regions = sorted({c.region for c in record.claims if c.region != "whole"}) or ["left_cuff", "collar", "hem"]
        res.closeup_request = random.Random(seed).choice(regions)
    return res
