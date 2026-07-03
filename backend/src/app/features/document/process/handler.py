"""Process-document use case: drives a document through ingestion.

Triggered by the background worker (see ``task.py``). The status transitions and
error recording live here; the actual NLP ingestion pipeline (owned by ML-1)
plugs into the marked extension point.
"""

import logging

from app.domain.exceptions.document import DocumentNotFoundError
from app.features.document.process.repository import ProcessDocumentRepository
from app.features.document.process.schemas import ProcessDocumentCommand

logger = logging.getLogger(__name__)


class ProcessDocumentHandler:
    """Marks a document as processing, runs ingestion, records the outcome."""

    def __init__(self, repository: ProcessDocumentRepository) -> None:
        self._repository = repository

    async def __call__(self, command: ProcessDocumentCommand) -> None:
        document = await self._repository.get(command.document_id)
        if document is None:
            raise DocumentNotFoundError(command.document_id)

        document.mark_processing()
        try:
            # TODO(ML-1): run the ingestion pipeline here — parse (PyMuPDF) →
            # chunk + language detect → LLM extraction → normalize → write to
            # Neo4j/Qdrant with provenance. Until then this is a no-op.
            document.mark_processed()
        except Exception as exc:
            # Worker boundary: record the failure on the document, never crash.
            logger.exception("document ingestion failed", extra={"document_id": str(document.id)})
            document.fail(str(exc))
