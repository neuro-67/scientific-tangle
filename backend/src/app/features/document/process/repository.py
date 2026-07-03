"""Persistence for the process-document use case."""

from app.domain.entities.document import Document
from app.infrastructure.repositories.base import SQLAlchemyRepository


class ProcessDocumentRepository(SQLAlchemyRepository[Document]):
    """Loads documents for status transitions during ingestion."""

    model_type = Document
