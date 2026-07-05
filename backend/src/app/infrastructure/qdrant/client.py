"""Qdrant adapter implementing the vector-search port.

Uses sync QdrantClient wrapped in asyncio.to_thread due to Python 3.14
compatibility issues with httpx/httpcore async.

If the client fails with WinError 10054 (connection reset), falls back to
raw HTTP via requests (which doesn't have this issue on Python 3.14).
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import requests
from qdrant_client import QdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    IsEmptyCondition,
    IsNullCondition,
    MatchValue,
    PayloadField,
    Range,
)

from app.domain.interfaces.vector_search import IVectorSearch
from app.infrastructure.qdrant.exceptions import VectorSearchError
from nlp.query.schemas import QuerySpec

logger = logging.getLogger(__name__)


class QdrantVectorSearch(IVectorSearch):
    """Qdrant adapter for semantic vector search."""

    def __init__(
        self,
        client: QdrantClient,
        collection: str = "chunks",
        host: str = "localhost",
        port: int = 6333,
    ) -> None:
        self._client = client
        self._collection = collection
        self._http_url = f"http://{host}:{port}/collections/{collection}/points/query"

    async def search(
        self,
        query_vector: list[float],
        spec: QuerySpec | None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        try:
            return await self._search_via_client(query_vector, spec, limit)
        except Exception as exc:
            err_str = str(exc).lower()
            if "10054" in str(exc) or "connection" in err_str:
                logger.warning("qdrant client connection reset, falling back to HTTP")
                return await self._search_via_http(query_vector, spec, limit)
            raise VectorSearchError(str(exc)) from exc

    async def _search_via_client(
        self,
        query_vector: list[float],
        spec: QuerySpec | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        filters = self._build_filters(spec)
        results = await asyncio.to_thread(
            self._client.query_points,
            collection_name=self._collection,
            query=query_vector,
            query_filter=filters,
            limit=limit,
            with_payload=True,
        )
        return [
            {
                "id": r.id,
                "score": r.score,
                # qdrant_upload.py writes source_document/entity_id (singular);
                # doc_id/entity_ids were the names this reader originally
                # expected -- keep both so either upload shape works.
                "doc_id": (r.payload.get("doc_id") or r.payload.get("source_document")) if r.payload else None,
                "page": r.payload.get("page") if r.payload else None,
                "lang": r.payload.get("lang") if r.payload else None,
                "entity_ids": (r.payload.get("entity_ids") or ([r.payload["entity_id"]] if r.payload.get("entity_id") else [])) if r.payload else [],
                "text": r.payload.get("text", "") if r.payload else "",
            }
            for r in results.points
        ]

    async def _search_via_http(
        self,
        query_vector: list[float],
        spec: QuerySpec | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fallback search using raw HTTP (avoids Python 3.14 client issues)."""
        payload: dict[str, Any] = {"query": query_vector, "limit": limit}
        filters = self._build_filters(spec)
        if filters is not None:
            payload["filter"] = filters.model_dump()

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(self._http_url, json=payload, timeout=30),
        )
        response.raise_for_status()
        data = response.json()

        points = data.get("result", {}).get("points", [])
        return [
            {
                "id": p.get("id"),
                "score": p.get("score"),
                "doc_id": p.get("payload", {}).get("doc_id") or p.get("payload", {}).get("source_document"),
                "page": p.get("payload", {}).get("page"),
                "lang": p.get("payload", {}).get("lang"),
                "entity_ids": p.get("payload", {}).get("entity_ids")
                or ([p["payload"]["entity_id"]] if p.get("payload", {}).get("entity_id") else []),
                "text": p.get("payload", {}).get("text", ""),
            }
            for p in points
        ]

    async def health(self) -> bool:
        try:
            await asyncio.to_thread(self._client.get_collections)
            return True
        except Exception:
            return False

    def _soft_match(self, key: str, value_condition: Any) -> Filter:
        """A filter that keeps points matching `value_condition` OR that have no
        value for `key` at all.

        Most nodes are ingested without a geography/year (~88% have
        geography=null, and nothing carries a `year` payload yet). A plain
        `must` match on those keys therefore discards the untagged majority and
        the query "finds nothing". Treat a missing/null tag as "unknown, don't
        exclude" so the filter only ever drops points that are *explicitly* the
        wrong geography/year.
        """
        return Filter(
            should=[
                value_condition,
                IsNullCondition(is_null=PayloadField(key=key)),
                IsEmptyCondition(is_empty=PayloadField(key=key)),
            ]
        )

    def _build_filters(self, spec: QuerySpec | None) -> Filter | None:
        """Build Qdrant payload filter from QuerySpec."""
        if spec is None:
            return None
        conditions: list[Any] = []

        if spec.geography.value != "any":
            conditions.append(
                self._soft_match(
                    "geography",
                    FieldCondition(
                        key="geography",
                        match=MatchValue(value=spec.geography.value),
                    ),
                )
            )

        if spec.time_range.from_year or spec.time_range.to_year:
            year_range = Range()
            if spec.time_range.from_year:
                year_range.gte = spec.time_range.from_year
            if spec.time_range.to_year:
                year_range.lte = spec.time_range.to_year
            conditions.append(
                self._soft_match("year", FieldCondition(key="year", range=year_range))
            )

        return Filter(must=conditions) if conditions else None
