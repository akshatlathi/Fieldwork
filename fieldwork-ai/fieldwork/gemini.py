"""Thin wrapper over google-genai: structured output, retries and a token log.

Every Gemini call in Fieldwork goes through `generate`, so cost and latency are
measured in one place (logs/cost.jsonl) for the results table.
"""

from __future__ import annotations

import json
import httpx
from io import BytesIO
import time
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from . import config

if config.USE_SYSTEM_CERTS:
    import truststore

    truststore.inject_into_ssl()

from google import genai
from google.genai import errors, types

T = TypeVar("T", bound=BaseModel)

_client: genai.Client | None = None


def client() -> genai.Client:
    global _client
    if _client is None:
        if config.USE_VERTEX:
            # Application Default Credentials (the Cloud Run service account).
            _client = genai.Client(vertexai=True, project=config.GCP_PROJECT, location=config.GCP_LOCATION)
        else:
            # Reads GEMINI_API_KEY from the environment; never pass the key in code.
            _client = genai.Client()
    return _client


def image_part(path: str | Path, mime: str = "image/jpeg") -> types.Part:
    from PIL import Image, ImageOps

    data = Path(path).read_bytes()
    with Image.open(BytesIO(data)) as image:
        if image.getexif().get(274, 1) not in (None, 1):
            # Phone JPEGs often store sideways pixels with an EXIF rotation.
            # Gemini can locate boxes on raw pixels while OpenCV/browser display
            # the rotated image. Send explicit upright pixels to remove ambiguity.
            upright = ImageOps.exif_transpose(image).convert("RGB")
            buffer = BytesIO()
            upright.save(buffer, format="JPEG", quality=95)
            data, mime = buffer.getvalue(), "image/jpeg"
    return types.Part.from_bytes(data=data, mime_type=mime)


def upload_video(path: str | Path) -> types.File | types.Part:
    """Vertex accepts inline short clips; the Developer API uses its Files API."""
    if config.USE_VERTEX:
        p = Path(path)
        from .video import inline_video
        data, mime = inline_video(p)
        return types.Part.from_bytes(data=data, mime_type=mime)
    f = client().files.upload(file=str(path))
    while f.state and f.state.name == "PROCESSING":
        time.sleep(2)
        f = client().files.get(name=f.name)
    return f


def _log(task: str, model: str, resp: Any, seconds: float) -> None:
    usage = getattr(resp, "usage_metadata", None)
    row = {
        "ts": time.time(),
        "task": task,
        "model": model,
        "seconds": round(seconds, 2),
        "in_tokens": getattr(usage, "prompt_token_count", None),
        "out_tokens": getattr(usage, "candidates_token_count", None),
        "thinking_tokens": getattr(usage, "thoughts_token_count", None),
    }
    with open(config.LOG_DIR / "cost.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")


def log_agent_event(task: str, model: str, event: Any, seconds: float) -> bool:
    """Record ADK response usage without prompt content; skip partial/non-LLM events.

    Seconds are time since the previous response, including intervening tool work.
    """
    if getattr(event, "partial", False) or getattr(event, "usage_metadata", None) is None:
        return False
    _log(task, model, event, seconds)
    return True


def generate(
    task: str,
    contents: list[Any],
    *,
    schema: type[T] | None = None,
    model: str | None = None,
    system: str | None = None,
    code_execution: bool = False,
    media_resolution: str | None = None,
    temperature: float | None = None,
    retries: int = 2,
    timeout_s: int = 180,
) -> T | types.GenerateContentResponse:
    """Call Gemini. With `schema`, returns a validated pydantic object; otherwise the raw response."""
    model = model or config.MODEL_FLASH
    cfg = types.GenerateContentConfig(
        system_instruction=system,
        temperature=temperature,
        http_options=types.HttpOptions(timeout=timeout_s * 1000),
    )
    if schema is not None:
        cfg.response_mime_type = "application/json"
        cfg.response_schema = schema
    if code_execution:
        cfg.tools = [types.Tool(code_execution=types.ToolCodeExecution())]
    if media_resolution:
        cfg.media_resolution = getattr(types.MediaResolution, f"MEDIA_RESOLUTION_{media_resolution.upper()}")

    # Try the requested model a couple of times, then each fallback model.
    chain = [model] + [m for m in config.MODEL_FALLBACKS if m and m != model]
    last_error: Exception | None = None
    for m in chain:
        delay = 2.0
        for attempt in range(retries):
            start = time.time()
            try:
                resp = client().models.generate_content(model=m, contents=contents, config=cfg)
            except httpx.TransportError as e:
                # Read-only generation may lose a connection before headers.
                # Bound retries just as for transient model-service errors.
                last_error = e
                if attempt < retries - 1:
                    time.sleep(delay)
                    delay *= 2
                continue
            except errors.APIError as e:
                last_error = e
                if getattr(e, "code", None) in (429, 499, 500, 503, 504):
                    if attempt < retries - 1:
                        time.sleep(delay)
                        delay *= 2
                    continue
                raise
            _log(task, m, resp, time.time() - start)
            if schema is None:
                return resp
            if resp.parsed is not None:
                return resp.parsed
            return schema.model_validate_json(resp.text)
    raise last_error or RuntimeError("Gemini call failed")
