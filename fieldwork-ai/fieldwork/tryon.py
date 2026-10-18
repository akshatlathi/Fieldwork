"""Virtual try-on PREVIEW (never evidence). Order of attempts:
  1. FW_USE_VERTEX=1: Vertex AI Virtual Try-On (model "virtual-try-on-001", client.models.recontext_image)
  2. Gemini image model with both images, told to keep the garment's visible flaws
  3. A cached demo file in data/demo/tryon/ (match on the garment file's stem, else the first file)
Every output carries a "PREVIEW" banner burned into the pixels."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import cv2
import numpy as np

from . import config, gemini, imgedit
from .gemini import types

VERTEX_MODEL = os.getenv("FW_MODEL_TRYON", "virtual-try-on-001")
BANNER = "PREVIEW - AI-generated, not evidence of fit or condition"
PROMPT = ("Dress the person in image 2 in THIS exact garment from image 1. Reproduce the garment faithfully: same colour, cut, "
          "fabric and every visible flaw (stains, holes, pilling, fading) exactly as in image 1; do not clean or improve it. "
          "Keep the person's pose and the background.")


def _label(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    bar = max(24, h // 14)
    out = img.copy()
    cv2.rectangle(out, (0, 0), (w, bar), (20, 20, 20), -1)
    cv2.putText(out, BANNER, (8, bar - bar // 3), cv2.FONT_HERSHEY_SIMPLEX, min(0.7, w / 900), (255, 255, 255), 1, cv2.LINE_AA)
    return out


def _vertex_client():
    from google import genai

    return genai.Client(vertexai=True, project=getattr(config, "GCP_PROJECT", None) or os.getenv("GOOGLE_CLOUD_PROJECT"),
                        location=getattr(config, "GCP_LOCATION", None) or os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"))


def _image(p: Path) -> types.Image:
    return types.Image(image_bytes=Path(p).read_bytes(), mime_type="image/png" if str(p).lower().endswith(".png") else "image/jpeg")


def _vertex(garment: Path, person: Path) -> np.ndarray:
    resp = _vertex_client().models.recontext_image(
        model=VERTEX_MODEL,
        source=types.RecontextImageSource(person_image=_image(person), product_images=[types.ProductImage(product_image=_image(garment))]))
    data = resp.generated_images[0].image.image_bytes
    return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)


def _gemini_image(garment: Path, person: Path) -> np.ndarray:
    return imgedit.edit_image(PROMPT, [garment, person], task="tryon_preview")


def _cached(garment: Path) -> np.ndarray:
    d = config.DATA_DIR / "demo" / "tryon"
    files = sorted(p for p in d.glob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg")) if d.exists() else []
    if not files:
        raise FileNotFoundError(f"no cached try-on in {d}")
    pick = next((p for p in files if p.stem.lower().startswith(Path(garment).stem.lower())), files[0])
    return cv2.imread(str(pick))


def preview(garment_image: str | Path, person_image: str | Path, out_dir: Path | None = None) -> Path:
    """Returns the path of a PNG whose pixels are labelled 'PREVIEW'. Raises RuntimeError listing why each method failed."""
    garment, person = Path(garment_image), Path(person_image)
    attempts = []
    if os.getenv("FW_USE_VERTEX") == "1":
        attempts.append(("vertex", _vertex))
    attempts += [("gemini", _gemini_image), ("cached", lambda g, p: _cached(g))]
    errors = []
    for name, fn in attempts:
        try:
            img = fn(garment, person)
            if img is None:
                raise RuntimeError("empty image")
            break
        except Exception as e:  # quota, auth, no cache: fall to the next method
            errors.append(f"{name}: {type(e).__name__}: {str(e)[:120]}")
    else:
        raise RuntimeError("try-on preview unavailable. " + " | ".join(errors))
    d = out_dir or (config.DATA_DIR / "tryon_out")
    d.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(garment.read_bytes() + person.read_bytes()).hexdigest()[:10]
    out = d / f"preview_{key}.png"
    cv2.imwrite(str(out), _label(img))
    return out
