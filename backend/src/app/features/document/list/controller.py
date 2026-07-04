"""HTTP transport for listing documents."""

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Query, status

from app.features.document.list.handler import ListDocumentsHandler, ListDocumentsQuery
from app.features.document.schemas import DocumentResponse

router = APIRouter(tags=["documents"])


@router.get(
    "/documents",
    response_model=list[DocumentResponse],
    status_code=status.HTTP_200_OK,
    summary="List documents",
    description="Paginated list of documents with ingestion status, newest first.",
)
@inject
async def list_documents(
    handler: FromDishka[ListDocumentsHandler],
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[DocumentResponse]:
    return await handler(ListDocumentsQuery(limit=limit, offset=offset))
