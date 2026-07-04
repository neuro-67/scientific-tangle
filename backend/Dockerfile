ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src:/app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY backend/pyproject.toml ./
COPY backend/README.md ./

RUN uv pip install --system --no-cache -e . \
    && uv pip install --system --no-cache \
        watchfiles ruff mypy pytest pytest-asyncio types-passlib types-python-jose aiosqlite

# nlp/ lives outside the backend/ project root (sibling directory) -- the query
# feature imports it directly (from nlp.query.schemas import ...) instead of
# duplicating schemas/retrieval logic, so it must be present on PYTHONPATH.
FROM base AS dev
COPY backend/. .
COPY nlp/. ./nlp/
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app/src"]

FROM base AS prod
COPY backend/. .
COPY nlp/. ./nlp/
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
