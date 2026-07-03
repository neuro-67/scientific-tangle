"""Read-side data access for the get-document use case."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.document.schemas import DocumentResponse
from app.infrastructure.database.tables.documents import documents_table


class GetDocumentRepository:
    """Projects a stored document straight into its response DTO."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_response(self, document_id: UUID) -> DocumentResponse | None:
        stmt = select(documents_table).where(documents_table.c.id == document_id)
        row = (await self._session.execute(stmt)).mappings().first()
        if row is None:
            return None
        return DocumentResponse.model_validate(dict(row))
