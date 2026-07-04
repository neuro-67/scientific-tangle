"""Domain port for vector search operations."""

from abc import ABC, abstractmethod
from typing import Any

from nlp.query.schemas import QuerySpec


class IVectorSearch(ABC):
    """Execute semantic vector search against Qdrant."""

    @abstractmethod
    async def search(
        self,
        query_vector: list[float],
        spec: QuerySpec,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Return ranked vector results matching the query vector and QuerySpec filters."""

    @abstractmethod
    async def health(self) -> bool:
        """Check if Qdrant is reachable."""
