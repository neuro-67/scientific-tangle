"""Response schemas shared across the document feature's use cases."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.entities.document import DocumentStatus


class DocumentResponse(BaseModel):
    """Public view of a document and its ingestion status."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    content_type: str
    size: int
    status: DocumentStatus
    error: str | None
    created_at: datetime
    updated_at: datetime
