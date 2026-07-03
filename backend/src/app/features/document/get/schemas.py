"""Query DTO for the get-document use case."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class GetDocumentQuery:
    """Identifies the document whose status is requested."""

    document_id: UUID
