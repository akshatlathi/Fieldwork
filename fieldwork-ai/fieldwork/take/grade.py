"""Our trained condition model at runtime: SigLIP 2 embedding -> ordinal heads ->
conformal grade set (e.g. [3, 4]) plus pilling, stain and hole probabilities."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np

from .. import config

MODEL_ID = "google/siglip2-base-patch16-224"
HEADS = config.ROOT / "models" / "heads.joblib"


@lru_cache(maxsize=1)
def _backbone():
    if config.USE_SYSTEM_CERTS:
        import truststore

        truststore.inject_into_ssl()
    from transformers import AutoModel, AutoProcessor

    return AutoProcessor.from_pretrained(MODEL_ID), AutoModel.from_pretrained(MODEL_ID).eval()


@lru_cache(maxsize=1)
def _heads() -> dict:
    return joblib.load(HEADS)


def embed(paths: list[Path]) -> np.ndarray:
    import torch
    from PIL import Image, ImageOps

    processor, model = _backbone()
    imgs = []
    for path in paths:
        with Image.open(path) as image:
            imgs.append(ImageOps.exif_transpose(image).convert("RGB"))
    with torch.inference_mode():
        f = model.get_image_features(**processor(images=imgs, return_tensors="pt"))
        f = getattr(f, "pooler_output", f)
        return torch.nn.functional.normalize(f, dim=-1).numpy()


def grade(paths: list[Path]) -> dict:
    """Average the per-frame probabilities over the given frames (front/back views)."""
    X = embed(paths)
    h = _heads()
    out = {}
    for name in ("condition", "pilling"):
        p = h[name]["head"].proba(X).mean(axis=0)
        levels = h[name]["levels"]
        keep = [levels[i] for i in np.where(1 - p <= h[name]["qhat"])[0]]
        out[name] = {"set": keep or [levels[int(p.argmax())]], "best": levels[int(p.argmax())], "proba": p.round(3).tolist()}
    for name in ("stains", "holes"):
        out[name] = float(h[name]["head"].predict_proba(X)[:, 1].mean())
    return out
