"""Command DTO for the delete-document use case."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DeleteDocumentCommand(BaseModel):
    """Request to remove a document and everything it produced downstream."""

    model_config = ConfigDict(frozen=True)

    document_id: UUID
