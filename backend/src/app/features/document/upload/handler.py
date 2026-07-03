"""Upload-document use case: store bytes, register the document, queue ingestion."""

from pathlib import PurePosixPath

from app.domain.entities.base import uuid7
from app.domain.entities.document import Document
from app.domain.interfaces.job_queue import IJobQueue
from app.domain.interfaces.object_storage import IObjectStorage
from app.features.document.upload.repository import UploadDocumentRepository
from app.features.document.upload.schemas import UploadDocumentCommand
from app.infrastructure.database.after_commit import AfterCommitQueue


class UploadDocumentHandler:
    """Stores an uploaded file and schedules its background ingestion.

    The processing job is enqueued only after the surrounding transaction
    commits, so the worker never looks up a document that is not yet visible.
    """

    def __init__(
        self,
        repository: UploadDocumentRepository,
        storage: IObjectStorage,
        job_queue: IJobQueue,
        after_commit: AfterCommitQueue,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._job_queue = job_queue
        self._after_commit = after_commit

    async def __call__(self, command: UploadDocumentCommand) -> Document:
        safe_name = PurePosixPath(command.filename).name or "upload"
        storage_key = f"{uuid7()}/{safe_name}"

        await self._storage.put(storage_key, command.content, command.content_type)

        document = Document.create(
            filename=command.filename,
            content_type=command.content_type,
            size=len(command.content),
            storage_key=storage_key,
        )
        await self._repository.add(document)

        document_id = document.id
        self._after_commit.add(
            lambda: self._job_queue.enqueue_document_processing(document_id)
        )
        return document
