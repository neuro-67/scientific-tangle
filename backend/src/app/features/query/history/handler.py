"""Read-side handlers + regenerate coordinator for the answer history."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, status

from app.features.query.ask.handler import AskQuestionHandler
from app.features.query.ask.schemas import AskQuestionCommand, AskQuestionResponse
from app.features.query.history.repository import AnswersRepository
from app.features.query.history.schemas import AnswerListItem, AnswerRecord


@dataclass(frozen=True, slots=True)
class ListAnswersQuery:
    limit: int = 50
    offset: int = 0


class ListAnswersHandler:
    def __init__(self, repository: AnswersRepository) -> None:
        self._repository = repository

    async def __call__(self, query: ListAnswersQuery) -> list[AnswerListItem]:
        return await self._repository.list_all(limit=query.limit, offset=query.offset)


class GetAnswerHandler:
    def __init__(self, repository: AnswersRepository) -> None:
        self._repository = repository

    async def __call__(self, answer_id: UUID) -> AnswerRecord:
        record = await self._repository.get_by_id(answer_id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found"
            )
        return record


class DeleteAnswerHandler:
    def __init__(self, repository: AnswersRepository) -> None:
        self._repository = repository

    async def __call__(self, answer_id: UUID) -> None:
        deleted = await self._repository.delete(answer_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found"
            )


class RegenerateAnswerHandler:
    """Re-runs the ask pipeline over the saved question and updates the row.

    Kept separate from AskQuestionHandler so the ask endpoint stays a single
    concern; this one owns the "look up old row → re-run → update" flow and
    fails fast if the row is gone.
    """

    def __init__(
        self,
        repository: AnswersRepository,
        ask_handler: AskQuestionHandler,
    ) -> None:
        self._repository = repository
        self._ask_handler = ask_handler

    async def __call__(self, answer_id: UUID) -> AskQuestionResponse:
        record = await self._repository.get_by_id(answer_id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found"
            )
        command = AskQuestionCommand(question=record.question)
        return await self._ask_handler(command, persist_as=answer_id)
