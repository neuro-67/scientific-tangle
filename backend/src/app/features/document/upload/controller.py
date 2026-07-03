"""HTTP transport for the upload-document use case."""

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, UploadFile, status

from app.features.document.schemas import DocumentResponse
from app.features.document.upload.handler import UploadDocumentHandler
from app.features.document.upload.schemas import UploadDocumentCommand

router = APIRouter(tags=["documents"])

_DEFAULT_CONTENT_TYPE = "application/octet-stream"


@router.post(
    "/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
@inject
async def upload_document(
    file: UploadFile,
    handler: FromDishka[UploadDocumentHandler],
) -> DocumentResponse:
    """Upload a document; it is stored and queued for ingestion."""
    command = UploadDocumentCommand(
        filename=file.filename or "upload",
        content_type=file.content_type or _DEFAULT_CONTENT_TYPE,
        content=await file.read(),
    )
    document = await handler(command)
    return DocumentResponse.model_validate(document)
