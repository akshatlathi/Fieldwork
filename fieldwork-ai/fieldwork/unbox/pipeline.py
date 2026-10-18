"""Received garment -> SigLIP pairing -> DINOv2/Gemini inspection -> suggested assessment.
The issue API saves this evidence in a human-review report; inspection never settles escrow."""

from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np

from ..spec import ConditionRecord
from ..store import store
from ..take import frames as fr
from ..take.grade import embed
from .gate import UnboxResult, check


def pair_frames(listing: dict[str, Path], unbox: list[Path], min_sim: float = 0.6) -> list[tuple[str, Path]]:
    if not listing or not unbox:
        return []
    ids = list(listing)
    A, B = embed([listing[i] for i in ids]), embed(unbox)
    sim = A @ B.T
    pairs = []
    for row, fid in enumerate(ids):
        # Keep a bounded set of semantically plausible alternatives. The gate
        # tries them in order only when the best view cannot be aligned.
        for j in np.argsort(-sim[row], kind="stable")[:3]:
            if sim[row, j] >= min_sim:
                pairs.append((fid, unbox[int(j)]))
    return pairs


def run_unbox(record: ConditionRecord, video: Path | None = None, photos: list[Path] | None = None,
              seed: int | None = None, work_name: str = "unbox") -> UnboxResult:
    d = store.item_dir(record.id)
    work = d / work_name
    work.mkdir(parents=True, exist_ok=True)
    received_labels = {}
    if video is not None:
        src = shutil.copyfile(video, work / ("unbox" + video.suffix.lower()))
        from ..video import validate_video
        validate_video(Path(src))
        selected = fr.evidence_candidates(fr.extract_frames(src, work / "frames"), k=10)
        frames = [f.path for f in selected]
        received_labels.update({str(f.path): f"Received video · {f.t:.2f}s · {f.frame_id}" for f in selected})
    else:
        frames = list(photos or [])
    if video is not None:
        frames.extend(photos or [])
    received_labels.update({str(p): f"Received photo {i+1}" for i, p in enumerate(photos or [])})
    for fid in record.capture.frames:
        store.get_file(record.id, f"{fid}.jpg")  # pulls listing frames from GCS on a fresh instance
    listing = {fid: d / f"{fid}.jpg" for fid in record.capture.frames if (d / f"{fid}.jpg").exists()}
    from ..regions import reference_masks
    metadata = store.get_json("listings", record.id) or {}
    masks = reference_masks(metadata.get("capture_coverage", {}), listing)
    res = check(record, listing, pair_frames(listing, frames), work / "crops", seed=seed,
                reference_masks=masks, require_garment_focus=True, received_labels=received_labels,
                listing_labels=metadata.get("frame_sources", {}))
    if len(listing) < len(record.capture.frames):
        res.limitations.append("Some listing evidence files were unavailable.")
        if res.verdict == "consistent":
            res.verdict = "cant_tell"
    store.put_json("unbox", record.id, {**res.__dict__, "findings": [f.__dict__ for f in res.findings]})
    store.sync_item(record.id)
    return res
