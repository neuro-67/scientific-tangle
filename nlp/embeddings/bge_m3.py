"""Embedding generator using sentence-transformers with mean pooling.

Works with any HuggingFace model. Default is all-MiniLM-L6-v2 (384-dim)
as a lightweight fallback when BAAI/bge-m3 is not available.

When BAAI/bge-m3 works, change the default model_name.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class BgeEmbeddingGenerator:
    """Generates dense embeddings using a sentence-transformers model.

    Default: all-MiniLM-L6-v2 (384-dim, fast, multilingual-ish)
    Target: BAAI/bge-m3 (1024-dim, full multilingual) when available
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        device: str = "cpu",
    ) -> None:
        self._model_name = model_name
        self._device = device
        self._model = None
        self._tokenizer = None
        self._dim = 384  # default for all-MiniLM-L6-v2
        self._load_model()

    def _load_model(self) -> None:
        """Attempt to load the embedding model."""
        try:
            from transformers import AutoModel, AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(self._model_name)
            self._model = AutoModel.from_pretrained(self._model_name)
            self._model.eval()

            # Detect embedding dimension from model config
            if hasattr(self._model.config, "hidden_size"):
                self._dim = self._model.config.hidden_size

            logger.info(
                "loaded embedding model",
                extra={"model": self._model_name, "dim": self._dim},
            )
        except Exception as exc:
            logger.warning(
                "embedding model not available, using zero vectors",
                extra={"error": str(exc)},
            )

    def encode(self, text: str) -> list[float]:
        """Generate embedding for a single text using mean pooling."""
        if not self._model or not self._tokenizer:
            return [0.0] * self._dim

        try:
            import torch

            inputs = self._tokenizer(
                text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512,
            )
            with torch.no_grad():
                outputs = self._model(**inputs)
                # Mean pooling
                attention_mask = inputs["attention_mask"]
                token_embeddings = outputs.last_hidden_state
                input_mask_expanded = (
                    attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
                )
                sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
                sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
                embedding = sum_embeddings / sum_mask

            # Normalize
            embedding = torch.nn.functional.normalize(embedding, p=2, dim=1)
            return embedding.squeeze().tolist()
        except Exception as exc:
            logger.warning("embedding failed, returning zeros", extra={"error": str(exc)})
            return [0.0] * self._dim

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts."""
        if not self._model or not self._tokenizer:
            return [[0.0] * self._dim for _ in texts]

        try:
            import torch

            inputs = self._tokenizer(
                texts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512,
            )
            with torch.no_grad():
                outputs = self._model(**inputs)
                attention_mask = inputs["attention_mask"]
                token_embeddings = outputs.last_hidden_state
                input_mask_expanded = (
                    attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
                )
                sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
                sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
                embeddings = sum_embeddings / sum_mask

            # Normalize
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
            return [emb.tolist() for emb in embeddings]
        except Exception as exc:
            logger.warning("batch embedding failed, returning zeros", extra={"error": str(exc)})
            return [[0.0] * self._dim for _ in texts]
