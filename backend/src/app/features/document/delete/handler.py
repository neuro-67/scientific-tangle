"""Delete-document use case: cascade cleanup across all downstream stores."""

import logging

from app.domain.exceptions.document import DocumentNotFoundError
from app.domain.interfaces.object_storage import IObjectStorage
from app.features.document.delete.repository import (
    DeleteDocumentRepository,
    Neo4jDocumentPurger,
    QdrantDocumentPurger,
)
from app.features.document.delete.schemas import DeleteDocumentCommand

logger = logging.getLogger(__name__)


class DeleteDocumentHandler:
    """Removes a document from every store it can touch.

    Order is chosen so a partial failure doesn't leave a dangling reference
    that would make the doc unreachable but keep its extracted knowledge
    lingering. Downstream cleanups (Neo4j, Qdrant, MinIO) are best-effort:
    an outage there shouldn't block the caller from getting rid of the row.
    The Postgres row is deleted last so the doc keeps showing up in the UI
    until the cascade is done.
    """

    def __init__(
        self,
        repository: DeleteDocumentRepository,
        graph_purger: Neo4jDocumentPurger,
        vector_purger: QdrantDocumentPurger,
        storage: IObjectStorage,
    ) -> None:
        self._repository = repository
        self._graph_purger = graph_purger
        self._vector_purger = vector_purger
        self._storage = storage

    async def __call__(self, command: DeleteDocumentCommand) -> None:
        row = await self._repository.get_row(command.document_id)
        if row is None:
            raise DocumentNotFoundError(command.document_id)

        filename: str = row["filename"]
        storage_key: str = row["storage_key"]

        # Graph first — largest fan-out, and users care most about knowledge
        # traces disappearing from queries.
        try:
            await self._graph_purger.purge(filename)
        except Exception:
            logger.exception("failed to purge Neo4j for %s", filename)

        try:
            await self._vector_purger.purge(filename)
        except Exception:
            logger.exception("failed to purge Qdrant for %s", filename)

        try:
            await self._storage.delete(storage_key)
        except Exception:
            logger.exception("failed to delete blob %s", storage_key)

        await self._repository.delete_row(command.document_id)
