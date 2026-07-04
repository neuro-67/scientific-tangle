"""Answer persistence — write from /query/ask, read from /answers/*."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.query.history.schemas import AnswerListItem, AnswerRecord
from app.infrastructure.database.tables.answers import answers_table


class AnswersRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        question: str,
        query_spec: dict[str, Any],
        synthesis: dict[str, Any],
        subgraph: dict[str, Any],
        confidence: str | None,
    ) -> AnswerRecord:
        now = datetime.now(tz=timezone.utc)
        answer_id = uuid4()
        row = {
            "id": answer_id,
            "question": question,
            "query_spec": query_spec,
            "synthesis": synthesis,
            "subgraph": subgraph,
            "confidence": confidence,
            "created_at": now,
            "updated_at": now,
        }
        await self._session.execute(answers_table.insert().values(**row))
        await self._session.commit()
        return AnswerRecord.model_validate(row)

    async def update(
        self,
        answer_id: UUID,
        *,
        query_spec: dict[str, Any],
        synthesis: dict[str, Any],
        subgraph: dict[str, Any],
        confidence: str | None,
    ) -> AnswerRecord | None:
        now = datetime.now(tz=timezone.utc)
        stmt = (
            update(answers_table)
            .where(answers_table.c.id == answer_id)
            .values(
                query_spec=query_spec,
                synthesis=synthesis,
                subgraph=subgraph,
                confidence=confidence,
                updated_at=now,
            )
            .returning(answers_table)
        )
        result = await self._session.execute(stmt)
        row = result.mappings().first()
        await self._session.commit()
        return AnswerRecord.model_validate(dict(row)) if row else None

    async def list_all(self, *, limit: int, offset: int) -> list[AnswerListItem]:
        cols = [
            answers_table.c.id,
            answers_table.c.question,
            answers_table.c.confidence,
            answers_table.c.created_at,
            answers_table.c.updated_at,
        ]
        stmt = (
            select(*cols)
            .order_by(answers_table.c.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).mappings().all()
        return [AnswerListItem.model_validate(dict(row)) for row in rows]

    async def get_by_id(self, answer_id: UUID) -> AnswerRecord | None:
        stmt = select(answers_table).where(answers_table.c.id == answer_id)
        row = (await self._session.execute(stmt)).mappings().first()
        return AnswerRecord.model_validate(dict(row)) if row else None

    async def delete(self, answer_id: UUID) -> bool:
        stmt = delete(answers_table).where(answers_table.c.id == answer_id)
        result = await self._session.execute(stmt)
        await self._session.commit()
        return (result.rowcount or 0) > 0
