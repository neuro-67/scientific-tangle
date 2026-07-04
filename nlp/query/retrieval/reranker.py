"""Cross-encoder reranker using bge-reranker-v2-m3 on GPU."""

from __future__ import annotations

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer


class CrossEncoderReranker:
    """GPU-accelerated cross-encoder reranker."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        device: str | None = None,
        max_length: int = 512,
    ) -> None:
        self._device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._max_length = max_length

        self._tokenizer = AutoTokenizer.from_pretrained(model_name)
        self._model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self._model.to(self._device)
        self._model.eval()

    def rerank(
        self,
        query: str,
        candidates: list[str],
        batch_size: int = 8,
    ) -> list[tuple[str, float]]:
        """Rerank candidates by relevance to query.

        Returns list of (candidate_text, score) sorted by score descending.
        """
        all_scores = []

        for i in range(0, len(candidates), batch_size):
            batch = candidates[i : i + batch_size]
            pairs = [[query, c] for c in batch]

            inputs = self._tokenizer(
                pairs,
                padding=True,
                truncation=True,
                max_length=self._max_length,
                return_tensors="pt",
            )
            inputs = {k: v.to(self._device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self._model(**inputs)
                scores = outputs.logits[:, 0].cpu().tolist()
                all_scores.extend(scores)

        ranked = sorted(
            zip(candidates, all_scores),
            key=lambda x: x[1],
            reverse=True,
        )
        return ranked

    def rerank_with_ids(
        self,
        query: str,
        candidates: list[dict],
        text_key: str = "text",
        top_k: int = 10,
    ) -> list[dict]:
        """Rerank candidate dicts and return top-k with scores added."""
        texts = [c.get(text_key, "") for c in candidates]
        scores = self.rerank(query, texts)

        # Merge scores back into candidates
        text_to_score = {t: s for t, s in scores}
        for c in candidates:
            c["rerank_score"] = text_to_score.get(c.get(text_key, ""), 0.0)

        return sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)[:top_k]
