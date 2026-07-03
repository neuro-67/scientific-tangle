"""Refresh-slice data access — verifies the subject still exists and is active."""

from uuid import UUID

from app.domain.entities.user import User
from app.infrastructure.database.mappers import row_to_user
from app.infrastructure.database.tables.user import UserRow
from app.infrastructure.repositories.base import BaseRepository


class RefreshRepository(BaseRepository):
    async def get_by_id(self, user_id: UUID) -> User | None:
        row = await self._session.get(UserRow, user_id)
        return row_to_user(row) if row is not None else None
