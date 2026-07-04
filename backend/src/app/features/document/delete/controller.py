"""HTTP transport for the delete-document use case."""

from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, status

from app.features.document.delete.handler import DeleteDocumentHandler
from app.features.document.delete.schemas import DeleteDocumentCommand

router = APIRouter(tags=["documents"])


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@inject
async def delete_document(
    document_id: UUID,
    handler: FromDishka[DeleteDocumentHandler],
) -> None:
    """Remove a document and everything it produced (graph, vectors, blob)."""
    await handler(DeleteDocumentCommand(document_id=document_id))
