"""Gemini image editing helper (text + image(s) in, image out). Used by the test bed, the forger
stress test and the try-on fallback. Model id comes from FW_MODEL_IMAGE; no model names in feature code."""

from __future__ import annotations

import os
import time
from pathlib import Path

import cv2
import numpy as np

from . import gemini
from .gemini import types

MODEL_IMAGE = os.getenv("FW_MODEL_IMAGE", "gemini-nano-banana-2.1")


def edit_image(prompt: str, images: list[Path | np.ndarray], model: str | None = None, task: str = "image_edit") -> np.ndarray:
    """Returns the first image the model produced as BGR uint8. Raises RuntimeError if it returned none."""
    model = model or MODEL_IMAGE
    parts: list = [prompt]
    for im in images:
        if isinstance(im, np.ndarray):
            parts.append(types.Part.from_bytes(data=cv2.imencode(".jpg", im, [cv2.IMWRITE_JPEG_QUALITY, 95])[1].tobytes(),
                                               mime_type="image/jpeg"))
        else:
            parts.append(gemini.image_part(im))
    start = time.time()
    resp = gemini.client().models.generate_content(
        model=model, contents=parts, config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]))
    try:
        gemini._log(task, model, resp, time.time() - start)
    except Exception:  # logging must never break an edit
        pass
    for cand in getattr(resp, "candidates", None) or []:
        for part in getattr(getattr(cand, "content", None), "parts", None) or []:
            data = getattr(getattr(part, "inline_data", None), "data", None)
            if data:
                img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
                if img is not None:
                    return img
    raise RuntimeError("image model returned no image")
