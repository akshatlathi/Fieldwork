"""One Take -> ConditionRecord -> listing in N languages, saved to the store.

    from fieldwork.take.pipeline import run_take
    record = run_take(Path("take.mp4"), code="K7Q2")            # video
    record = run_take(None, code=None, photos=[p1, p2, p3])     # camera-roll fallback (weaker badge)
"""

from __future__ import annotations

import hashlib
import shutil
import uuid
from pathlib import Path

from pydantic import BaseModel

from .. import config, gemini
from ..spec import Capture, ConditionRecord
from ..store import store
from . import frames as fr
from . import grade as gr
from .record import draft_record, to_claims, coverage_report

LANGS = {"ja": "Japanese", "ko": "Korean", "zh-TW": "Traditional Chinese", "th": "Thai", "id-ID": "Indonesian", "vi": "Vietnamese", "hi": "Hindi"}

class Translations(BaseModel):
    ja: str
    ko: str
    zh_TW: str
    th: str
    id: str
    vi: str
    hi: str


def translate(text_en: str) -> dict[str, str]:
    t = gemini.generate(
        "translate_listing",
        ["Translate this second-hand listing faithfully (keep flaws explicit, no hype) into: "
         + ", ".join(LANGS.values()) + ".\n\n" + text_en],
        schema=Translations,
        model=config.MODEL_LITE,
        temperature=0,
    )
    d = t.model_dump()
    d["zh-TW"] = d.pop("zh_TW")
    d["id-ID"] = d.pop("id")  # plain "id" would clash with the listing id
    return d


def run_take(video: Path | None, code: str | None, photos: list[Path] | None = None, item_id: str | None = None,
             *, attempt_id: str = "", translate_listing: bool = True) -> ConditionRecord:
    item_id = item_id or f"g_{uuid.uuid4().hex[:8]}"
    d = store.item_dir(item_id)
    prefix = f"{attempt_id}_" if attempt_id else ""
    frame_sources = {}

    if video is not None:
        from ..video import validate_video
        validate_video(video)
        src = store.put_file(item_id, video, prefix + "take" + video.suffix.lower())
        digest = hashlib.sha256(src.read_bytes()).hexdigest()
        chosen = fr.evidence_candidates(fr.extract_frames(src, d / (prefix + "all_frames")), k=8)
        kept = []
        for i, f in enumerate(chosen):
            fid = f"{prefix}f{i + 1}"
            frame_sources[fid] = f"Seller video · {f.t:.2f}s · {fid}"
            shutil.copyfile(f.path, d / f"{fid}.jpg")
            kept.append((fid, d / f"{fid}.jpg"))
    else:
        digest = hashlib.sha256(b"".join(p.read_bytes() for p in photos or [])).hexdigest()
        kept = []
        for i, p in enumerate(photos or []):
            fid = f"{prefix}p{i + 1}"
            frame_sources[fid] = f"Seller photo {i+1} · {fid}"
            shutil.copyfile(p, d / f"{fid}.jpg")
            kept.append((fid, d / f"{fid}.jpg"))

    # A video overview and independently captured close-ups are complementary.
    # Previously photos supplied with a video were silently ignored.
    if video is not None:
        for i, path in enumerate(photos or []):
            fid = f"{prefix}p{i + 1}"
            frame_sources[fid] = f"Seller photo {i+1} · {fid}"
            shutil.copyfile(path, d / f"{fid}.jpg")
            kept.append((fid, d / f"{fid}.jpg"))

    if not kept:
        raise ValueError("No usable garment frames were captured")
    draft = draft_record(store.item_dir(item_id) / (prefix + "take" + video.suffix.lower()) if video else None, kept)
    claims = to_claims(draft, {fid for fid, _ in kept})
    coverage = coverage_report(draft, {fid for fid, _ in kept})
    # Retain all cited evidence; remove redundant uncited candidates from the
    # reference set used during later inspection, without deleting source frames.
    if draft.coverage:
        cited = {b.frame_id for c in claims for b in c.evidence}
        cited.update(b["frame_id"] for v in coverage["views"] for b in v["evidence"])
        if cited:
            kept = [(fid, path) for fid, path in kept if fid in cited]
    g = gr.grade([p for _, p in kept[:4]])
    code_seen = bool(code and draft.code_read and draft.code_read.strip().upper() == code.strip().upper())

    record = ConditionRecord(
        id=item_id,
        item=draft.item,
        claims=claims,
        grade_set=[int(x) for x in g["condition"]["set"]],
        price_band=None, currency="INR",
        capture=Capture(code_expected=code or "none", code_seen=code_seen, take_sha256=digest, frames=[fid for fid, _ in kept]),
        listing_text_en=draft.listing_text_en,
    )
    listing = {"id": item_id, "en": draft.listing_text_en, **(translate(draft.listing_text_en) if translate_listing else {}),
               "model_grade": g, "evidence_badge": "strong" if (video and code_seen) else "basic",
               "capture_coverage": coverage, "frame_sources": frame_sources, "publication_status": "draft"}
    store.sync_item(item_id)  # no-op locally; uploads frames/video to GCS in the cloud
    store.put_json("listings", item_id, listing)
    store.put_json("records", item_id, record.model_dump(mode="json"))
    return record
