"""Read-side data access for the list-documents use case."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.document.schemas import DocumentResponse
from app.infrastructure.database.tables.documents import documents_table


class ListDocumentsRepository:
    """Projects stored documents straight into their response DTOs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self, *, limit: int, offset: int) -> list[DocumentResponse]:
        stmt = (
            select(documents_table)
            .order_by(documents_table.c.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).mappings().all()
        return [DocumentResponse.model_validate(dict(row)) for row in rows]
