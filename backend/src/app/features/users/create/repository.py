"""Create-slice data access."""

from sqlalchemy import select

from app.domain.entities.user import User
from app.infrastructure.database.mappers import user_to_row
from app.infrastructure.database.tables.user import UserRow
from app.infrastructure.repositories.base import BaseRepository


class CreateUserRepository(BaseRepository):
    async def exists_by_username(self, username: str) -> bool:
        stmt = select(UserRow.id).where(UserRow.username == username)
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def add(self, user: User) -> None:
        self._session.add(user_to_row(user))
        await self._session.flush()
