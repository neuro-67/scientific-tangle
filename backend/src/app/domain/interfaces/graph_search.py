"""Domain port for graph search operations."""

from abc import ABC, abstractmethod
from typing import Any

from nlp.query.schemas import QuerySpec


class IGraphSearch(ABC):
    """Execute structured queries against the knowledge graph."""

    @abstractmethod
    async def search(self, spec: QuerySpec, limit: int = 20) -> list[dict[str, Any]]:
        """Return ranked graph results matching the QuerySpec."""

    @abstractmethod
    async def get_entity_context(self, entity_name: str, entity_type: str) -> dict[str, Any] | None:
        """Return neighbourhood context for a specific entity node."""

    @abstractmethod
    async def fetch_subgraph(self, spec: QuerySpec, node_limit: int = 30) -> dict[str, Any]:
        """Return {'nodes': [...], 'edges': [...]} around entries matched by spec.

        Used to render the answer's subgraph on the client. Same matching logic
        as `search` (primary label branch → meta-node fallback), then expands
        one hop out and returns deduplicated nodes/edges.
        """
