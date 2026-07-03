"""Get-document use case: returns a document's current status."""

from app.domain.exceptions.document import DocumentNotFoundError
from app.features.document.get.repository import GetDocumentRepository
from app.features.document.get.schemas import GetDocumentQuery
from app.features.document.schemas import DocumentResponse


class GetDocumentHandler:
    """Returns the requested document or raises if it is unknown."""

    def __init__(self, repository: GetDocumentRepository) -> None:
        self._repository = repository

    async def __call__(self, query: GetDocumentQuery) -> DocumentResponse:
        response = await self._repository.get_response(query.document_id)
        if response is None:
            raise DocumentNotFoundError(query.document_id)
        return response
