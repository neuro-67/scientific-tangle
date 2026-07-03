"""Document aggregate: a source file moving through the ingestion pipeline."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Self

from app.domain.clock import now_utc
from app.domain.entities.base import BaseEntity
from app.domain.events.document import DocumentUploadedEvent
from app.domain.exceptions.document import DocumentStateError


class DocumentStatus(StrEnum):
    """Lifecycle states of a document in the ingestion pipeline."""

    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


@dataclass(kw_only=True)
class Document(BaseEntity):
    """An uploaded source document. Aggregate root for its ingestion lifecycle.

    Invariants:
        - status transitions follow PENDING -> PROCESSING -> PROCESSED/FAILED.
        - error is set only while status is FAILED.
    """

    filename: str
    content_type: str
    size: int
    storage_key: str
    status: DocumentStatus
    error: str | None = None

    @classmethod
    def create(cls, *, filename: str, content_type: str, size: int, storage_key: str) -> Self:
        """Register a freshly uploaded document awaiting processing."""
        document = cls(
            filename=filename,
            content_type=content_type,
            size=size,
            storage_key=storage_key,
            status=DocumentStatus.PENDING,
        )
        document.record(
            DocumentUploadedEvent(document_id=document.id, storage_key=storage_key)
        )
        return document

    def mark_processing(self) -> None:
        """Move a pending document into active processing."""
        if self.status is not DocumentStatus.PENDING:
            raise DocumentStateError(self.id, self.status, DocumentStatus.PROCESSING)
        self.status = DocumentStatus.PROCESSING
        self.updated_at = now_utc()

    def mark_processed(self) -> None:
        """Mark a document whose ingestion completed successfully."""
        if self.status is not DocumentStatus.PROCESSING:
            raise DocumentStateError(self.id, self.status, DocumentStatus.PROCESSED)
        self.status = DocumentStatus.PROCESSED
        self.error = None
        self.updated_at = now_utc()

    def fail(self, reason: str) -> None:
        """Mark ingestion as failed, recording the reason."""
        self.status = DocumentStatus.FAILED
        self.error = reason
        self.updated_at = now_utc()
