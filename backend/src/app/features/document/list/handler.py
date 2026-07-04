"""List-documents use case (read slice)."""

from dataclasses import dataclass

from app.features.document.list.repository import ListDocumentsRepository
from app.features.document.schemas import DocumentResponse


@dataclass(frozen=True, slots=True)
class ListDocumentsQuery:
    limit: int = 50
    offset: int = 0


class ListDocumentsHandler:
    def __init__(self, repository: ListDocumentsRepository) -> None:
        self._repository = repository

    async def __call__(self, query: ListDocumentsQuery) -> list[DocumentResponse]:
        return await self._repository.list_all(limit=query.limit, offset=query.offset)
