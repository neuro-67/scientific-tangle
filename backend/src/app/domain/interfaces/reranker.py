"""Domain port for reranking retrieved results."""

from abc import ABC, abstractmethod
from typing import Any


class IReranker(ABC):
    """Rerank retrieved results by relevance to a query."""

    @abstractmethod
    def rerank(
        self,
        query: str,
        results: list[dict[str, Any]],
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Return results reordered by relevance score."""
