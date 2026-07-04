"""Process-document use case: drives a document through ingestion.

Triggered by the background worker (see ``task.py``). The status transitions
live here; the actual NLP ingestion (parse -> chunk -> extract -> normalize ->
write to Neo4j/Qdrant, owned by ML-1) is delegated to ingestion.py.
"""

import logging

from app.domain.exceptions.document import DocumentNotFoundError
from app.domain.interfaces.object_storage import IObjectStorage
from app.features.document.process.ingestion import run_ingestion_pipeline
from app.features.document.process.repository import ProcessDocumentRepository
from app.features.document.process.schemas import ProcessDocumentCommand

logger = logging.getLogger(__name__)


class ProcessDocumentHandler:
    """Marks a document as processing, runs ingestion, records the outcome."""

    def __init__(self, repository: ProcessDocumentRepository, storage: IObjectStorage) -> None:
        self._repository = repository
        self._storage = storage

    async def __call__(self, command: ProcessDocumentCommand) -> None:
        document = await self._repository.get(command.document_id)
        if document is None:
            raise DocumentNotFoundError(command.document_id)

        try:
            # mark_processing() lives inside the try too: it can itself raise
            # DocumentStateError (e.g. arq redelivering a job whose previous
            # attempt never got to record a terminal state for some other
            # reason), and that must still result in fail(), not an uncaught
            # exception that leaves the document stuck with no status update.
            document.mark_processing()
            file_bytes = await self._storage.get(document.storage_key)
            stats = await run_ingestion_pipeline(
                file_bytes, document.filename, document.content_type
            )
            logger.info(
                "document ingestion complete",
                extra={"document_id": str(document.id), **stats},
            )
            document.mark_processed()
        except (Exception, SystemExit) as exc:
            # nlp.run_corpus_test raises SystemExit at import time if
            # ROUTERAI_API_KEY is unset -- caught here too so a misconfigured
            # env fails this one document instead of killing the arq worker.
            logger.exception("document ingestion failed", extra={"document_id": str(document.id)})
            document.fail(str(exc))
