"""Command DTO for the process-document use case."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ProcessDocumentCommand:
    """Identifies the document whose ingestion should run."""

    document_id: UUID
