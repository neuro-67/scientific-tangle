"""HTTP routes for answer history: list, get, delete, regenerate."""

from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Query, status

from app.features.query.ask.schemas import AskQuestionResponse
from app.features.query.history.handler import (
    DeleteAnswerHandler,
    GetAnswerHandler,
    ListAnswersHandler,
    ListAnswersQuery,
    RegenerateAnswerHandler,
)
from app.features.query.history.schemas import AnswerListItem, AnswerRecord

router = APIRouter(tags=["answers"])


@router.get(
    "/answers",
    response_model=list[AnswerListItem],
    status_code=status.HTTP_200_OK,
    summary="List saved answers",
)
@inject
async def list_answers(
    handler: FromDishka[ListAnswersHandler],
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[AnswerListItem]:
    return await handler(ListAnswersQuery(limit=limit, offset=offset))


@router.get(
    "/answers/{answer_id}",
    response_model=AnswerRecord,
    status_code=status.HTTP_200_OK,
    summary="Get a saved answer with the full envelope",
)
@inject
async def get_answer(
    answer_id: UUID,
    handler: FromDishka[GetAnswerHandler],
) -> AnswerRecord:
    return await handler(answer_id)


@router.delete(
    "/answers/{answer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a saved answer",
)
@inject
async def delete_answer(
    answer_id: UUID,
    handler: FromDishka[DeleteAnswerHandler],
) -> None:
    await handler(answer_id)


@router.post(
    "/answers/{answer_id}/regenerate",
    response_model=AskQuestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Re-run the pipeline over the saved question and update the row",
)
@inject
async def regenerate_answer(
    answer_id: UUID,
    handler: FromDishka[RegenerateAnswerHandler],
) -> AskQuestionResponse:
    return await handler(answer_id)
