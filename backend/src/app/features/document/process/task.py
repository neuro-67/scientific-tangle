"""Background entry point for the process-document use case.

Registered as an arq task (see ``features/registry/tasks.py``). It adapts the
job arguments into the command and drives the handler inside a fresh
request-scoped DI container, whose session provider commits on success.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

from app.features.document.process.handler import ProcessDocumentHandler
from app.features.document.process.schemas import ProcessDocumentCommand

if TYPE_CHECKING:
    from dishka import AsyncContainer


async def process_document(ctx: dict[str, Any], document_id: str) -> None:
    """Run ingestion for the given document id."""
    container: AsyncContainer = ctx["container"]
    async with container() as request_container:
        handler = await request_container.get(ProcessDocumentHandler)
        await handler(ProcessDocumentCommand(document_id=UUID(document_id)))
