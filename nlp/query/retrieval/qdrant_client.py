"""Qdrant vector search client."""

from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, Range

from nlp.query.schemas import QuerySpec


class QdrantSearchClient:
    """Qdrant client for semantic vector search."""

    def __init__(self, host: str = "localhost", port: int = 6333, collection: str = "chunks") -> None:
        self._client = QdrantClient(host=host, port=port)
        self._collection = collection

    def health(self) -> bool:
        try:
            self._client.get_collections()
            return True
        except Exception:
            return False

    def search(
        self,
        query_vector: list[float],
        spec: QuerySpec,
        limit: int = 20,
    ) -> list[dict]:
        """Search Qdrant with vector + payload filters from QuerySpec."""
        filters = self._build_filters(spec)
        results = self._client.search(
            collection_name=self._collection,
            query_vector=query_vector,
            query_filter=filters,
            limit=limit,
            with_payload=True,
        )
        return [
            {
                "id": r.id,
                "score": r.score,
                "doc_id": r.payload.get("doc_id"),
                "page": r.payload.get("page"),
                "lang": r.payload.get("lang"),
                "entity_ids": r.payload.get("entity_ids", []),
                "text": r.payload.get("text", ""),
            }
            for r in results
        ]

    def _build_filters(self, spec: QuerySpec) -> Filter | None:
        """Build Qdrant payload filter from QuerySpec."""
        conditions = []

        # Geography filter
        if spec.geography.value != "any":
            conditions.append(
                FieldCondition(
                    key="geography",
                    match=MatchValue(value=spec.geography.value),
                )
            )

        # Time range filter
        if spec.time_range.from_year or spec.time_range.to_year:
            year_range = Range()
            if spec.time_range.from_year:
                year_range.gte = spec.time_range.from_year
            if spec.time_range.to_year:
                year_range.lte = spec.time_range.to_year
            conditions.append(FieldCondition(key="year", range=year_range))

        # Sensitivity / RBAC filter would go here
        # conditions.append(FieldCondition(key="sensitivity", match=MatchValue(value="public")))

        return Filter(must=conditions) if conditions else None
