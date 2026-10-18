"""Frame extraction and quality scoring for the seller's take (video or single photos)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

BLUR_THRESHOLD = 12.0  # variance of Laplacian at 640px wide; plain-background garment shots are low-texture, blur sits at ~1-5
DARK, BRIGHT = 40.0, 235.0


@dataclass
class Frame:
    frame_id: str
    path: Path
    t: float
    sharpness: float
    brightness: float


def _gray_metrics(img: np.ndarray) -> tuple[float, float]:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    if w != 640:
        gray = cv2.resize(gray, (640, max(1, round(h * 640 / w))), interpolation=cv2.INTER_AREA)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var()), float(gray.mean())


def extract_frames(video_path: str | Path, out_dir: str | Path, every_s: float = 0.25) -> list[Frame]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, round(every_s * fps))
    frames: list[Frame] = []
    i = 0
    while True:
        ok, img = cap.read()
        if not ok:
            break
        if i % step == 0:
            fid = f"f{len(frames):04d}"
            path = out / f"{fid}.jpg"
            cv2.imwrite(str(path), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
            sharp, bright = _gray_metrics(img)
            frames.append(Frame(fid, path, i / fps, sharp, bright))
        i += 1
    cap.release()
    return frames


def select_frames(frames: list[Frame], k: int = 8, min_gap_s: float = 0.75) -> list[Frame]:
    usable = [f for f in frames if DARK < f.brightness < BRIGHT]
    chosen: list[Frame] = []
    for f in sorted(usable, key=lambda f: -f.sharpness):
        if all(abs(f.t - c.t) >= min_gap_s for c in chosen):
            chosen.append(f)
        if len(chosen) == k:
            break
    return sorted(chosen, key=lambda f: f.t)


def quality_report(frames: list[Frame]) -> dict:
    n = len(frames) or 1
    return {
        "n_frames": len(frames),
        "duration_s": round(max((f.t for f in frames), default=0.0), 2),
        "blurry_share": round(sum(f.sharpness < BLUR_THRESHOLD for f in frames) / n, 3),
        "too_dark_share": round(sum(f.brightness <= DARK for f in frames) / n, 3),
        "too_bright_share": round(sum(f.brightness >= BRIGHT for f in frames) / n, 3),
    }


def evidence_candidates(frames: list[Frame], k: int = 8) -> list[Frame]:
    """Preserve the sharpness baseline and add time coverage; at most 2*k frames.

    This is a candidate pool for semantic inspection, not a claim that every
    required garment view is present. Never replace a sharp baseline view.
    """
    if k < 1 or not frames:
        return []
    chosen = {f.frame_id: f for f in select_frames(frames, k=k)}
    end = max(f.t for f in frames) + 1e-6
    bins: list[list[Frame]] = [[] for _ in range(k)]
    for f in frames:
        if DARK < f.brightness < BRIGHT:
            bins[min(k - 1, int(f.t / end * k))].append(f)
    for bucket in bins:
        if bucket:
            best = max(bucket, key=lambda f: f.sharpness)
            chosen[best.frame_id] = best
    return sorted(chosen.values(), key=lambda f: f.t)


def image_quality(path: str | Path) -> dict:
    img = cv2.imread(str(path))
    sharp, bright = _gray_metrics(img)
    return {
        "sharpness": round(sharp, 1),
        "brightness": round(bright, 1),
        "blurry": sharp < BLUR_THRESHOLD,
        "too_dark": bright <= DARK,
        "too_bright": bright >= BRIGHT,
        "width": img.shape[1],
        "height": img.shape[0],
    }
