"""Cross-encoder reranker using BAAI/bge-reranker-v2-m3.

This is a placeholder implementation. The actual model loading is deferred
due to Python 3.14 + onnxruntime compatibility issues (segfault).

When the environment supports it, uncomment the model loading code.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """Reranks retrieved results using a cross-encoder model.

    Placeholder: returns results as-is. Full implementation requires:
    - transformers + torch
    - BAAI/bge-reranker-v2-m3 (568M, 8K context, multilingual)
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3") -> None:
        self._model_name = model_name
        self._model = None
        self._tokenizer = None
        self._load_model()

    def _load_model(self) -> None:
        """Attempt to load the cross-encoder model."""
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(self._model_name)
            self._model = AutoModelForSequenceClassification.from_pretrained(self._model_name)
            self._model.eval()
            logger.info("loaded cross-encoder model", extra={"model": self._model_name})
        except Exception as exc:
            logger.warning(
                "cross-encoder model not available, using identity reranker",
                extra={"error": str(exc)},
            )

    def rerank(
        self,
        query: str,
        results: list[dict[str, Any]],
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Rerank results by relevance to the query."""
        if not self._model or not results:
            # Identity fallback: return top_k as-is
            return results[:top_k]

        try:
            import torch

            # Prepare pairs: (query, result_text)
            texts = [r.get("text", r.get("finding_text", "")) for r in results]
            pairs = [(query, text) for text in texts]

            # Tokenize
            inputs = self._tokenizer(
                pairs,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            )

            # Score
            with torch.no_grad():
                scores = self._model(**inputs).logits.squeeze(-1)

            # Attach scores and sort
            scored_results = []
            for r, score in zip(results, scores.tolist()):
                r_copy = dict(r)
                r_copy["rerank_score"] = score
                scored_results.append(r_copy)

            scored_results.sort(key=lambda x: x["rerank_score"], reverse=True)
            return scored_results[:top_k]

        except Exception as exc:
            logger.warning("reranking failed, returning as-is", extra={"error": str(exc)})
            return results[:top_k]
