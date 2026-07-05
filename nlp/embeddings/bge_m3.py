"""Embedding generator backed by RouterAI's hosted BAAI/bge-m3.

We can't run bge-m3 locally -- torch/transformers aren't installed in the
backend/worker image, so the old local-model path always fell back to zero
vectors, which silently killed semantic search (every Qdrant query scored 0).
RouterAI exposes bge-m3 (multilingual, 1024-dim) over an OpenAI-compatible
/embeddings endpoint, so we call that instead. Same interface (encode /
encode_batch) as before, so nothing downstream changes.

Falls back to zero vectors only if no API key is configured or the call
fails, so ingestion/query degrade instead of crashing.
"""

from __future__ import annotations

import logging
import os
import time

import requests

logger = logging.getLogger(__name__)

_MODEL = "baai/bge-m3"
_DIM = 1024
_BATCH = 64
# RouterAI's hosted bge-m3 flaps: individual requests intermittently 503
# ("HTTP 503: Error") or time out even though the next try succeeds. Without
# retries a single blip makes _embed fall back to a zero vector, which for a
# *query* embedding silently kills semantic search for that whole request
# (every Qdrant score collapses to 0 -> "finds nothing"). Retry transient
# failures with backoff before giving up.
_RETRIES = 4
_BACKOFF = (0.5, 1.0, 2.0, 4.0)


class BgeEmbeddingGenerator:
    """Generates dense multilingual embeddings via RouterAI's bge-m3."""

    def __init__(self, model_name: str = _MODEL, device: str = "cpu") -> None:
        # device kept for signature compatibility; RouterAI runs the model.
        self._model_name = model_name
        self._dim = _DIM
        self._api_key = os.environ.get("ROUTERAI_API_KEY", "")
        self._base_url = os.environ.get("ROUTERAI_BASE_URL", "https://routerai.ru/api/v1").rstrip("/")
        if not self._api_key:
            logger.warning("ROUTERAI_API_KEY not set -- embeddings will be zero vectors")

    @property
    def dim(self) -> int:
        return self._dim

    def _embed(self, inputs: list[str]) -> list[list[float]]:
        if not self._api_key or not inputs:
            return [[0.0] * self._dim for _ in inputs]
        last_err: str | None = None
        for attempt in range(_RETRIES):
            try:
                resp = requests.post(
                    f"{self._base_url}/embeddings",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"model": self._model_name, "input": inputs},
                    timeout=60,
                )
                # 5xx / 429 are transient (upstream flap or rate limit) -> retry;
                # 4xx (bad key, bad request) won't fix itself -> stop retrying.
                if resp.status_code >= 500 or resp.status_code == 429:
                    last_err = f"HTTP {resp.status_code}: {resp.text[:120]}"
                    raise requests.HTTPError(last_err)
                resp.raise_for_status()
                data = resp.json()["data"]
                # Preserve request order (RouterAI returns an "index" per item).
                ordered = sorted(data, key=lambda d: d.get("index", 0))
                return [item["embedding"] for item in ordered]
            except requests.HTTPError as exc:
                last_err = str(exc)
                # Only retry the transient statuses flagged above.
                if "HTTP 5" not in last_err and "HTTP 429" not in last_err:
                    break
            except Exception as exc:  # timeout / connection reset -> retry
                last_err = str(exc)
            if attempt < _RETRIES - 1:
                time.sleep(_BACKOFF[min(attempt, len(_BACKOFF) - 1)])
        logger.warning(
            "embedding request failed after retries, returning zeros",
            extra={"error": last_err, "n": len(inputs)},
        )
        return [[0.0] * self._dim for _ in inputs]

    def encode(self, text: str) -> list[float]:
        """Embed a single string."""
        return self._embed([text])[0]

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed many strings, chunked to keep each request small."""
        out: list[list[float]] = []
        for i in range(0, len(texts), _BATCH):
            out.extend(self._embed(texts[i : i + _BATCH]))
        return out
