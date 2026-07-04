"""Persistence for the delete-document use case.

Owns the Postgres row lifecycle only. Cross-store cleanup (Neo4j / Qdrant /
MinIO) is orchestrated by the handler using their respective ports so the
repository stays focused on relational storage.
"""

import logging
from typing import Any
from uuid import UUID

from neo4j import AsyncDriver
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import FieldCondition, Filter, FilterSelector, MatchValue
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.tables.documents import documents_table

logger = logging.getLogger(__name__)


class DeleteDocumentRepository:
    """Reads the doc metadata and deletes the Postgres row."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_row(self, document_id: UUID) -> dict[str, Any] | None:
        stmt = select(documents_table).where(documents_table.c.id == document_id)
        row = (await self._session.execute(stmt)).mappings().first()
        return dict(row) if row else None

    async def delete_row(self, document_id: UUID) -> None:
        await self._session.execute(
            delete(documents_table).where(documents_table.c.id == document_id)
        )
        await self._session.commit()


class Neo4jDocumentPurger:
    """Removes all nodes and relationships tagged with a given source filename."""

    def __init__(self, driver: AsyncDriver) -> None:
        self._driver = driver

    async def purge(self, source_document: str) -> tuple[int, int]:
        """Delete rels and nodes with ``source_document = filename``.

        Rels are dropped first so DETACH DELETE on nodes doesn't have to do
        anything about relationships that will be gone anyway. Returns
        ``(rels_deleted, nodes_deleted)`` for logging.
        """
        async with self._driver.session() as session:
            rels_res = await session.run(
                "MATCH ()-[r]->() WHERE r.source_document = $doc DELETE r RETURN count(r) AS n",
                {"doc": source_document},
            )
            rels_row = await rels_res.single()
            rels_deleted = int(rels_row["n"]) if rels_row else 0

            nodes_res = await session.run(
                "MATCH (n) WHERE n.source_document = $doc DETACH DELETE n RETURN count(n) AS n",
                {"doc": source_document},
            )
            nodes_row = await nodes_res.single()
            nodes_deleted = int(nodes_row["n"]) if nodes_row else 0

            logger.info(
                "neo4j purge for %s: %d rels, %d nodes",
                source_document,
                rels_deleted,
                nodes_deleted,
            )
            return rels_deleted, nodes_deleted


class QdrantDocumentPurger:
    """Removes all vectors whose payload references the given document."""

    def __init__(self, client: QdrantClient, collection: str = "chunks") -> None:
        self._client = client
        self._collection = collection

    async def purge(self, source_document: str) -> None:
        # Chunks are tagged with `source_document` (canonical) and older
        # payloads may have `doc_id`. Try both so old ingestions don't leak.
        import asyncio

        def _delete_by_key(key: str) -> None:
            try:
                self._client.delete(
                    collection_name=self._collection,
                    points_selector=FilterSelector(
                        filter=Filter(
                            must=[
                                FieldCondition(
                                    key=key,
                                    match=MatchValue(value=source_document),
                                )
                            ]
                        )
                    ),
                )
            except UnexpectedResponse as exc:
                # Collection doesn't exist yet — nothing to purge.
                if "404" in str(exc) or "not found" in str(exc).lower():
                    return
                raise

        try:
            await asyncio.to_thread(_delete_by_key, "source_document")
            await asyncio.to_thread(_delete_by_key, "doc_id")
        except Exception:
            # Non-fatal: log and swallow so the rest of the cascade still runs.
            logger.exception("qdrant purge failed for %s", source_document)
