"""Login-slice data access."""

from sqlalchemy import select

from app.domain.entities.user import User
from app.infrastructure.database.mappers import row_to_user
from app.infrastructure.database.tables.user import UserRow
from app.infrastructure.repositories.base import BaseRepository


class LoginRepository(BaseRepository):
    async def find_by_username(self, username: str) -> User | None:
        stmt = select(UserRow).where(UserRow.username == username)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return row_to_user(row) if row is not None else None
