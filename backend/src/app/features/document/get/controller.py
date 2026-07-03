"""HTTP transport for the get-document use case."""

from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, status

from app.features.document.get.handler import GetDocumentHandler
from app.features.document.get.schemas import GetDocumentQuery
from app.features.document.schemas import DocumentResponse

router = APIRouter(tags=["documents"])


@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
)
@inject
async def get_document(
    document_id: UUID,
    handler: FromDishka[GetDocumentHandler],
) -> DocumentResponse:
    """Return a document's metadata and ingestion status."""
    return await handler(GetDocumentQuery(document_id=document_id))
