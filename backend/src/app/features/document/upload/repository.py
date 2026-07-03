"""Persistence for the upload-document use case."""

from app.domain.entities.document import Document
from app.infrastructure.repositories.base import SQLAlchemyRepository


class UploadDocumentRepository(SQLAlchemyRepository[Document]):
    """Adds new documents to the store."""

    model_type = Document
