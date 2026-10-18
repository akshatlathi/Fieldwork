"""Planted-change test bed from existing listing frames.  SYNTHETIC STRESS TEST, NOT THE HEADLINE METRIC.

For each frame: pick a region, ask Gemini image editing (FW_MODEL_IMAGE) to add ONE small realistic
stain/hole/snag there, then composite ONLY that region back onto the untouched original, so every
other pixel is identical to the source. Saves pairs + labels.json under data/results/testbed/.

    uv run python eval/testbed.py --frames "data/test_cv/ref*.jpg" --n 6
    uv run python eval/testbed.py --frames "store/items/*/f1.jpg" --n 20 --evaluate   # also run the change detector

The real headline metric is the physically planted changes in run_eval.py.
"""

from __future__ import annotations

import argparse
import glob
import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fieldwork import config, imgedit  # noqa: E402
from fieldwork.stats import fmt, rate  # noqa: E402

KINDS = {
    "stain": "a small realistic stain (about 1 cm across, e.g. a coffee or ink splash)",
    "hole": "a small realistic hole or burn mark (about 5 mm) with slightly frayed edges",
    "snag": "a small realistic snagged or pulled thread loop",
}
DISCLAIMER = "SYNTHETIC STRESS TEST: planted by an image model on listing frames; not the headline metric."


def pick_box(shape: tuple[int, int], rng: random.Random, side_frac: tuple[float, float] = (0.12, 0.18)) -> list[int]:
    """[ymin,xmin,ymax,xmax] in 0-1000, inside the central 60% of the frame (most garment, least background)."""
    s = rng.uniform(*side_frac) * 1000
    y0, x0 = rng.uniform(200, 800 - s), rng.uniform(200, 800 - s)
    return [round(y0), round(x0), round(y0 + s), round(x0 + s)]


def box_px(box: list[int], shape: tuple[int, int]) -> tuple[int, int, int, int]:
    h, w = shape[:2]
    return round(box[0] * h / 1000), round(box[1] * w / 1000), round(box[2] * h / 1000), round(box[3] * w / 1000)


def composite_region(orig: np.ndarray, edited: np.ndarray, box: list[int], feather_px: int = 6) -> np.ndarray:
    """Copy `edited` into `orig` ONLY inside the box (soft edge kept inside the box); the rest stays pixel-identical."""
    h, w = orig.shape[:2]
    if edited.shape[:2] != (h, w):
        edited = cv2.resize(edited, (w, h), interpolation=cv2.INTER_AREA)
    y0, x0, y1, x1 = box_px(box, orig.shape)
    mask = np.zeros((h, w), np.float32)
    mask[y0:y1, x0:x1] = 1.0
    if feather_px > 0:
        inner = np.zeros_like(mask)
        inner[y0 + feather_px:y1 - feather_px, x0 + feather_px:x1 - feather_px] = 1.0
        soft = cv2.GaussianBlur(inner, (0, 0), feather_px / 2)
        mask = np.minimum(mask, np.maximum(soft, 0)) if inner.sum() else mask
    m3 = mask[..., None]
    out = (orig.astype(np.float32) * (1 - m3) + edited.astype(np.float32) * m3).round().astype(np.uint8)
    return out


def plant(frame: Path, kind: str, box: list[int], edit=None) -> tuple[np.ndarray, np.ndarray]:
    orig = cv2.imread(str(frame))
    y0, x0, y1, x1 = box_px(box, orig.shape)
    prompt = (f"Edit this photo of a garment: add exactly ONE {KINDS[kind]} located inside the region from "
              f"(x={x0}px, y={y0}px) to (x={x1}px, y={y1}px). Change nothing else; keep the same framing, lighting and fabric texture.")
    edited = (edit or imgedit.edit_image)(prompt, [frame], task="testbed_edit")
    return orig, composite_region(orig, edited, box)


def build(frames: list[Path], out: Path, n: int, seed: int, edit=None) -> list[dict]:
    rng = random.Random(seed)
    out.mkdir(parents=True, exist_ok=True)
    labels = []
    for i, f in enumerate(frames[:n]):
        kind = rng.choice(list(KINDS))
        box = pick_box(cv2.imread(str(f)).shape[:2], rng)
        try:
            orig, planted = plant(f, kind, box, edit)
        except Exception as e:
            labels.append({"id": f"tb{i:03d}", "source": str(f), "error": f"{type(e).__name__}: {e}"[:200]})
            continue
        a, b = out / f"tb{i:03d}_orig.jpg", out / f"tb{i:03d}_planted.jpg"
        cv2.imwrite(str(a), orig, [cv2.IMWRITE_JPEG_QUALITY, 95])
        cv2.imwrite(str(b), planted, [cv2.IMWRITE_JPEG_QUALITY, 95])
        # identical outside the box (checked on the unsaved arrays; JPEG re-encoding is lossy)
        y0, x0, y1, x1 = box_px(box, orig.shape)
        keep = np.ones(orig.shape[:2], bool)
        keep[y0:y1, x0:x1] = False
        labels.append({"id": f"tb{i:03d}", "source": str(f), "orig": str(a), "planted": str(b), "kind": kind, "box_2d": box,
                       "outside_identical": bool((orig[keep] == planted[keep]).all()), "synthetic": True})
    (out / "labels.json").write_text(json.dumps({"disclaimer": DISCLAIMER, "labels": labels}, indent=2), encoding="utf-8")
    return labels


def evaluate(labels: list[dict], regions_fn=None, judge_fn=None, min_score: float | None = None) -> dict:
    """Run the production change finder + Gemini judge on each pair (already pixel-aligned, so no align step)."""
    from fieldwork.unbox import diff, judge
    from fieldwork.unbox.gate import MIN_CHANGE_SCORE

    regions_fn, judge_fn = regions_fn or diff.change_regions, judge_fn or judge.compare
    min_score = MIN_CHANGE_SCORE if min_score is None else min_score
    ok = [lb for lb in labels if "planted" in lb]
    hit = 0
    for lb in ok:
        y0, x0, y1, x1 = lb["box_2d"]
        found = False
        for r in regions_fn(lb["orig"], lb["planted"], top_k=3):
            cy, cx = (r.box_2d[0] + r.box_2d[2]) / 2, (r.box_2d[1] + r.box_2d[3]) / 2
            if r.score >= min_score and y0 - 40 <= cy <= y1 + 40 and x0 - 40 <= cx <= x1 + 40:
                ca, cb = diff.crop_pair(lb["orig"], lb["planted"], r.box_2d, out_dir=Path(lb["planted"]).parent / "crops")
                v = judge_fn(ca, cb)
                found = found or (v.new_defect and v.severity in ("minor", "major"))
        lb["detected"] = found
        hit += found
    return {"label": DISCLAIMER, "recall_on_synthetic_plants": rate(hit, len(ok))}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True, help="glob of listing frames")
    ap.add_argument("--out", type=Path, default=config.DATA_DIR / "results" / "testbed")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--evaluate", action="store_true")
    a = ap.parse_args(argv)
    frames = [Path(p) for p in sorted(glob.glob(a.frames))]
    labels = build(frames, a.out, a.n, a.seed)
    print(f"{sum('planted' in lb for lb in labels)}/{len(labels)} pairs written to {a.out}  [{DISCLAIMER}]")
    if a.evaluate:
        res = evaluate(labels)
        (a.out / "testbed_results.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
        print(DISCLAIMER, "recall:", fmt(res["recall_on_synthetic_plants"]))


if __name__ == "__main__":
    main()
