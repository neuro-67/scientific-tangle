"""HTTP transport for the ask-question use case."""

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, status

from app.features.query.ask.handler import AskQuestionHandler
from app.features.query.ask.schemas import AskQuestionCommand, AskQuestionResponse

router = APIRouter(prefix="/query", tags=["query"])


@router.post(
    "/ask",
    response_model=AskQuestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a question",
    description="Parse a natural-language question, search the knowledge graph, and synthesize an answer.",
)
@inject
async def ask_question(
    command: AskQuestionCommand,
    handler: FromDishka[AskQuestionHandler],
) -> AskQuestionResponse:
    """Submit a natural-language question and receive a structured answer."""
    return await handler(command)
