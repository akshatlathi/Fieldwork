"""CV smoke test: plant a stain in a transformed copy, align, diff, and report. Run: uv run python tests/test_cv.py"""

import io
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from fieldwork.take.frames import extract_frames, select_frames, quality_report  # noqa: E402
from fieldwork.unbox.align import align  # noqa: E402
from fieldwork.unbox.diff import change_regions  # noqa: E402

OUT = ROOT / "data" / "test_cv"
OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(0)


def load_images(n=3):
    t = pq.read_table(ROOT / "data/hf/data/test-00000-of-00001.parquet", columns=["image"])
    for i in range(n):
        raw = t.column("image")[i].as_py()["bytes"]
        img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
        s = 900 / max(img.shape[:2])
        yield cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s < 1 else img


def garment_mask(img):
    bg = np.median(np.concatenate([img[:10].reshape(-1, 3), img[-10:].reshape(-1, 3)]), axis=0)
    d = np.linalg.norm(img.astype(np.float32) - bg, axis=-1)
    m = (d > 25).astype(np.uint8)
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))


def plant_stain(img, mask):
    ys, xs = np.nonzero(mask)
    area = len(ys)
    cy, cx = np.percentile(ys, 55), np.percentile(xs, 45)  # inside the garment body
    r = np.sqrt(0.04 * area / np.pi)
    a, b = r * 1.3, r / 1.3
    st = np.zeros(img.shape[:2], np.float32)
    cv2.ellipse(st, (int(cx), int(cy)), (int(a), int(b)), 25, 0, 360, 1.0, -1)
    st = cv2.GaussianBlur(st, (0, 0), 3) * (0.55 + 0.15 * cv2.GaussianBlur(rng.random(st.shape).astype(np.float32), (0, 0), 6) / 0.05 * 0.05)
    col = np.array([45, 85, 135], np.float32)  # BGR brown
    out = img.astype(np.float32) * (1 - st[..., None]) + col * st[..., None] * (img.astype(np.float32).mean(-1, keepdims=True) / 140).clip(0.5, 1.2)
    box = [cy - b - 4, cx - a - 4, cy + b + 4, cx + a + 4]
    h, w = img.shape[:2]
    return out.clip(0, 255).astype(np.uint8), [box[0] / h * 1000, box[1] / w * 1000, box[2] / h * 1000, box[3] / w * 1000]


def transform(img, stain_box=None):
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), 8, 0.9)
    M[:, 2] += (0.03 * w, -0.02 * h)
    bg = tuple(int(v) for v in np.median(np.concatenate([img[:10].reshape(-1, 3), img[-10:].reshape(-1, 3)]), axis=0))
    out = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderValue=bg)
    out = (out.astype(np.float32) * 1.15 + 8 - 128) * 1.12 + 128  # brightness / contrast
    out = out + rng.normal(0, 2, out.shape)
    return cv2.GaussianBlur(out.clip(0, 255).astype(np.uint8), (0, 0), 0.8)


def iou(a, b):
    y0, x0, y1, x1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    i = max(0, y1 - y0) * max(0, x1 - x0)
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i)


def hit(box, gt):
    cy, cx = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return iou(box, gt) > 0.1 or (gt[0] <= cy <= gt[2] and gt[1] <= cx <= gt[3])


def transform_box(gt, shape):
    """Map the planted stain box through the same similarity transform (as a bounding box of its corners)."""
    return gt  # ground truth is expressed in the *reference* frame, which is what change_regions returns


imgs = list(load_images())
found3 = 0
for i, ref in enumerate(imgs):
    rp = OUT / f"ref{i}.jpg"
    cv2.imwrite(str(rp), ref)
    stained, gt = plant_stain(ref, garment_mask(ref))
    hp, cp = OUT / f"handover{i}.jpg", OUT / f"clean{i}.jpg"
    cv2.imwrite(str(hp), transform(stained))
    cv2.imwrite(str(cp), transform(ref))
    t0 = time.time()
    ar = align(rp, hp)
    regs = change_regions(rp, ar.warped_path) if ar.ok else []
    dt = time.time() - t0
    rank = next((k + 1 for k, r in enumerate(regs) if hit(r.box_2d, gt)), None)
    found3 += bool(rank and rank <= 3)
    print(f"pair{i}: aligned={ar.ok} inliers={ar.inliers} ratio={ar.inlier_ratio:.2f} stain_rank={rank} "
          f"top={[(r.box_2d, r.score, r.kind_hint) for r in regs[:3]]} gt={[round(v) for v in gt]} time={dt:.1f}s")
    ac = align(rp, cp)
    rc = change_regions(rp, ac.warped_path) if ac.ok else []
    print(f"  no-stain: aligned={ac.ok} top_score={rc[0].score if rc else None} (stained top1 score={regs[0].score if regs else None})")
print(f"stain in top-3: {found3}/3")

# synthetic video: gentle motion, blurred segment 1.5-2.5s
src = imgs[0]
h, w = src.shape[:2]
fps, vid = 20, OUT / "synthetic.mp4"
vw = cv2.VideoWriter(str(vid), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w - 60, h - 60))
for n in range(4 * fps):
    t = n / fps
    dx, dy = int(30 + 20 * np.sin(t * 3)), int(30 + 15 * np.cos(t * 2))
    f = src[dy:dy + h - 60, dx:dx + w - 60].copy()
    if 1.5 <= t < 2.5:
        f = cv2.GaussianBlur(f, (0, 0), 6)
    vw.write(f)
vw.release()
fr = extract_frames(vid, OUT / "frames")
sel = select_frames(fr, k=4, min_gap_s=0.75)
bad = [f for f in sel if 1.5 <= f.t < 2.5]
print("frames:", len(fr), "report:", quality_report(fr))
print("sharp (clear) median:", round(float(np.median([f.sharpness for f in fr if not 1.5 <= f.t < 2.5])), 1),
      "blurred median:", round(float(np.median([f.sharpness for f in fr if 1.5 <= f.t < 2.5])), 1))
print("selected t:", [round(f.t, 2) for f in sel], "blurred picked:", len(bad))
