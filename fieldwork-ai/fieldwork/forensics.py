"""Two cheap image-forensics signals against AI-edited or pasted regions in an unbox frame.

These are heuristics, not proof: thresholds are UNCALIBRATED defaults. eval/forger.py reports the
score distribution on clean frames so they can be set from data. Use only to route a take to a
human / close-up request (cant_tell), never to accuse.

- ELA (error level analysis): re-save at JPEG q=90; regions with a different compression history
  than the rest change by a different amount. Score = (max block - median block) / (median + 1).
- JPEG-grid inconsistency: a once-compressed photo has blockiness aligned to the 8px grid across the
  frame; a pasted/resized region breaks that locally. Score = p95 - median of per-tile grid strength.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

# Set just above the clean-frame maxima seen on 8 product photos (ELA<=2.8, grid<=0.65). They have NO proven power against
# whole-image AI regeneration (they did not separate edits from clean frames in a first check): treat as a weak extra signal.
ELA_THRESHOLD = 4.0
GRID_THRESHOLD = 1.0
OFFSET = 1.0  # grey levels; stops flat backgrounds (near-zero variation) from inflating ratios
BLOCK = 32


@dataclass
class ForensicsResult:
    flagged: bool
    ela_score: float
    grid_score: float
    reasons: list[str] = field(default_factory=list)


def _robust_peak(block_vals: np.ndarray) -> float:
    med = float(np.median(block_vals))
    return (float(block_vals.max()) - med) / (med + OFFSET)


def ela_score(img_bgr: np.ndarray, quality: int = 90) -> float:
    ok, buf = cv2.imencode(".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    re = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    d = np.abs(img_bgr.astype(np.float32) - re.astype(np.float32)).mean(axis=-1)
    h, w = d.shape
    h, w = h // BLOCK * BLOCK, w // BLOCK * BLOCK
    if h == 0 or w == 0:
        return 0.0
    blocks = d[:h, :w].reshape(h // BLOCK, BLOCK, w // BLOCK, BLOCK).mean(axis=(1, 3)).ravel()
    return _robust_peak(blocks)


def grid_score(img_bgr: np.ndarray) -> float:
    g = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    dx = np.abs(np.diff(g, axis=1))  # dx[:, i] is the step between column i and i+1
    h, w = dx.shape
    h, w = h // BLOCK * BLOCK, (w // BLOCK) * BLOCK
    if h == 0 or w == 0:
        return 0.0
    dx = dx[:h, :w]
    edge = (np.arange(w) % 8) == 7  # steps across an 8px block boundary
    strengths = []
    for y in range(0, h, BLOCK):
        for x in range(0, w, BLOCK):
            t = dx[y:y + BLOCK, x:x + BLOCK]
            e, ne = t[:, edge[x:x + BLOCK]].mean(), t[:, ~edge[x:x + BLOCK]].mean()
            strengths.append((e - ne) / (ne + OFFSET))
    s = np.array(strengths)
    return float(np.percentile(s, 95) - np.median(s))


def check(path: str | Path) -> ForensicsResult:
    img = cv2.imread(str(path))
    e, g = ela_score(img), grid_score(img)
    reasons = []
    if e > ELA_THRESHOLD:
        reasons.append(f"error-level inconsistency in one block (score {e:.1f})")
    if g > GRID_THRESHOLD:
        reasons.append(f"JPEG-grid inconsistency across the frame (score {g:.2f})")
    return ForensicsResult(bool(reasons), round(e, 2), round(g, 3), reasons)
