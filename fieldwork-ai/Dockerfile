# Fieldwork API (FastAPI + ADK agents + our condition model) for Cloud Run, CPU only.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy FW_SYSTEM_CERTS=0 PORT=8080

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY fieldwork ./fieldwork
COPY models ./models
# Bake model weights into the image so cold starts don't download them.
RUN uv run python -c "from transformers import AutoModel, AutoProcessor; \
[(AutoProcessor.from_pretrained(m), AutoModel.from_pretrained(m)) for m in ('google/siglip2-base-patch16-224',)]; \
from transformers import AutoImageProcessor; AutoImageProcessor.from_pretrained('facebook/dinov2-small'); AutoModel.from_pretrained('facebook/dinov2-small')"

CMD ["sh", "-c", "uv run --no-sync uvicorn fieldwork.api:app --host 0.0.0.0 --port ${PORT}"]
