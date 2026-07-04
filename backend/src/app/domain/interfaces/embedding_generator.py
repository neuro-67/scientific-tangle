"""Domain port for embedding generation."""

from abc import ABC, abstractmethod


class IEmbeddingGenerator(ABC):
    """Generate dense vector embeddings from text."""

    @abstractmethod
    def encode(self, text: str) -> list[float]:
        """Return a dense embedding vector for the given text."""
