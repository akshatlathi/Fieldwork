"""Propose changed regions with public DINOv2 spatial features and Lab colour differences."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from .. import config
from ..evidence import valid_box

WORK_SIDE = 560  # multiple of DINOv2's 14px patch
PATCH_SIZE = 14
MODEL_ID = config.DINO_MODEL
_model = None


class InsufficientComparisonArea(ValueError):
    """No-change and insufficient evidence must remain distinguishable."""


@dataclass
class Region:
    box_2d: list[int]  # [ymin, xmin, ymax, xmax], 0-1000
    score: float
    kind_hint: str  # "colour" | "texture"


def _dino():
    global _model
    if _model is None:
        import truststore

        truststore.inject_into_ssl()
        import torch
        from transformers import AutoImageProcessor, AutoModel

        torch.set_num_threads(max(1, torch.get_num_threads()))
        try:
            proc = AutoImageProcessor.from_pretrained(MODEL_ID)
            _model = (proc, AutoModel.from_pretrained(MODEL_ID).eval())
        except OSError as exc:
            raise RuntimeError("DINOv2 weights unavailable. Check network access or pre-download the public checkpoint.") from exc
    return _model


def _patch_feats(img_bgr: np.ndarray):
    import torch

    proc, model = _dino()
    h, w = img_bgr.shape[:2]
    inp = proc(images=cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB), return_tensors="pt", do_resize=True,
               size={"height": h, "width": w}, do_center_crop=False)
    with torch.no_grad():
        output = model(**inp).last_hidden_state
    return _spatial_tokens(output, model.config, h, w)


def _spatial_tokens(output, model_config, h: int, w: int):
    """Exclude CLS and register tokens; fail visibly on a mismatched spatial layout."""
    patch = model_config.patch_size
    prefix = 1 + getattr(model_config, "num_register_tokens", 0)
    tokens = output[0, prefix:]
    expected = (h // patch) * (w // patch)
    if len(tokens) != expected:
        raise ValueError(f"DINO spatial token count {len(tokens)} does not match {expected}")
    return tokens.reshape(h // patch, w // patch, -1)


def _dino_map(ref: np.ndarray, new: np.ndarray) -> np.ndarray:
    import torch.nn.functional as F

    a, b = _patch_feats(ref), _patch_feats(new)
    d = 1 - F.cosine_similarity(a, b, dim=-1)
    return cv2.resize(d.numpy(), (ref.shape[1], ref.shape[0]), interpolation=cv2.INTER_CUBIC)


def _lab_map(ref: np.ndarray, new: np.ndarray, valid: np.ndarray) -> np.ndarray:
    a = cv2.cvtColor(cv2.GaussianBlur(ref, (0, 0), 3), cv2.COLOR_BGR2LAB).astype(np.float32)
    b = cv2.cvtColor(cv2.GaussianBlur(new, (0, 0), 3), cv2.COLOR_BGR2LAB).astype(np.float32)
    m = valid > 0
    ma, sa = a[..., 0][m].mean(), a[..., 0][m].std() + 1e-6
    mb, sb = b[..., 0][m].mean(), b[..., 0][m].std() + 1e-6
    b[..., 0] = (b[..., 0] - mb) / sb * sa + ma
    # remove any residual global colour cast too, so only local differences remain
    for c in (1, 2):
        b[..., c] += np.median(a[..., c][m]) - np.median(b[..., c][m])
    return np.linalg.norm(a - b, axis=-1)


def _z(m: np.ndarray, valid: np.ndarray, floor: float) -> np.ndarray:
    """Robust z-score; the floor stops a flat background (MAD ~ 0) from inflating every tiny difference."""
    v = m[valid > 0]
    med = np.median(v)
    return np.clip((m - med) / max(1.4826 * np.median(np.abs(v - med)), floor), 0, 12)


def change_regions(ref_path: str | Path, aligned_path: str | Path, valid_mask: np.ndarray | None = None,
                   top_k: int = 5, *, method: str = "combined") -> list[Region]:
    if method not in ("combined", "colour"):
        raise ValueError("Unknown candidate method")
    ref = cv2.imread(str(ref_path))
    new = cv2.imread(str(aligned_path))
    s = WORK_SIDE / max(ref.shape[:2])
    h, w = (max(PATCH_SIZE, round(ref.shape[0] * s) // PATCH_SIZE * PATCH_SIZE),
            max(PATCH_SIZE, round(ref.shape[1] * s) // PATCH_SIZE * PATCH_SIZE))
    ref = cv2.resize(ref, (w, h), interpolation=cv2.INTER_AREA)
    new = cv2.resize(new, (w, h), interpolation=cv2.INTER_AREA)

    if valid_mask is None:
        valid_mask = (new.max(axis=-1) > 8).astype(np.uint8)
        valid_mask = cv2.morphologyEx(valid_mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    else:
        valid_mask = cv2.resize((valid_mask > 0).astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST)
    valid = cv2.erode(valid_mask, np.ones((2 * round(0.03 * max(h, w)) + 1,) * 2, np.uint8), borderType=cv2.BORDER_CONSTANT,
                      borderValue=0)
    if valid.sum() < 0.05 * h * w:
        raise InsufficientComparisonArea("Too little valid area after excluding alignment borders")

    zd = _z(_dino_map(ref, new), valid, 0.08) if method == "combined" else np.zeros((h, w), np.float32)
    zl = _z(_lab_map(ref, new, valid), valid, 3.0)
    # Preserve the production weights; the colour ablation simply removes DINO's contribution.
    comb = cv2.GaussianBlur(0.5 * zd + 0.5 * zl, (0, 0), 4) * valid
    zd_s, zl_s = cv2.GaussianBlur(zd, (0, 0), 4), cv2.GaussianBlur(zl, (0, 0), 4)

    vals = comb[valid > 0]
    thr = max(cv2.threshold(np.clip(comb / max(comb.max(), 1e-6) * 255, 0, 255).astype(np.uint8), 0, 255,
                            cv2.THRESH_BINARY + cv2.THRESH_OTSU)[0] / 255 * comb.max(), np.percentile(vals, 90))
    mask = (comb > thr).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask)
    regions: list[Region] = []
    for i in range(1, n):
        x, y, bw, bh, area = stats[i]
        if area < 0.0005 * h * w:
            continue
        comp = lab == i
        score = float(np.percentile(comb[comp], 90))
        kind = "colour" if zl_s[comp].mean() >= 0.6 * zd_s[comp].mean() else "texture"  # Lab z runs lower than DINO z
        box = [round(y / h * 1000), round(x / w * 1000), round((y + bh) / h * 1000), round((x + bw) / w * 1000)]
        regions.append(Region(box, round(score, 3), kind))
    return sorted(regions, key=lambda r: -r.score)[:top_k]


def comparable_box(mask: np.ndarray, box: list[int], pad: float = 0.15) -> bool:
    h, w = mask.shape
    y0, x0, y1, x1 = box
    dy, dx = (y1-y0)*pad, (x1-x0)*pad
    area = mask[int(max(0,y0-dy)*h/1000):int(np.ceil(min(1000,y1+dy)*h/1000)),
                int(max(0,x0-dx)*w/1000):int(np.ceil(min(1000,x1+dx)*w/1000))]
    return bool(area.size and np.mean(area > 0) >= .95)


def crop_pair(ref_path: str | Path, aligned_path: str | Path, box_2d: list[int], pad: float = 0.15,
              out_dir: str | Path = ".") -> tuple[Path, Path]:
    if not valid_box(box_2d):
        raise ValueError("Evidence crop must have positive area within 0–1000")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    ref = cv2.imread(str(ref_path))
    new = cv2.imread(str(aligned_path))
    if ref is None or new is None:
        raise ValueError("Comparison image could not be read")
    if new.shape[:2] != ref.shape[:2]:
        raise ValueError("Comparison images must already share the aligned coordinate system")
    h, w = ref.shape[:2]
    y0, x0, y1, x1 = box_2d
    ph, pw = (y1 - y0) * pad, (x1 - x0) * pad
    y0, y1 = max(0, y0 - ph), min(1000, y1 + ph)
    x0, x1 = max(0, x0 - pw), min(1000, x1 + pw)
    sl = (slice(int(y0 * h / 1000), int(np.ceil(y1 * h / 1000))), slice(int(x0 * w / 1000), int(np.ceil(x1 * w / 1000))))
    tag = "_".join(str(v) for v in box_2d)
    rp, np_ = out / f"ref_{tag}.jpg", out / f"new_{tag}.jpg"
    cv2.imwrite(str(rp), ref[sl])
    cv2.imwrite(str(np_), new[sl])
    return rp, np_
