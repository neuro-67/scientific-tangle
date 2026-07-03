"""Domain events for the document aggregate."""

from dataclasses import dataclass
from uuid import UUID

from app.domain.events.base import DomainEvent


@dataclass(frozen=True)
class DocumentUploadedEvent(DomainEvent):
    """A document's bytes were stored and it is awaiting processing."""

    document_id: UUID
    storage_key: str
