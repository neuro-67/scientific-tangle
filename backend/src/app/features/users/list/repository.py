"""Read-slice repository: projects UserRow straight into UserResponse."""

from sqlalchemy import select

from app.domain.entities.user import UserRole
from app.features.users.schemas import UserResponse
from app.infrastructure.database.tables.user import UserRow
from app.infrastructure.repositories.base import BaseRepository


class ListUsersRepository(BaseRepository):
    async def list_all(self, *, limit: int, offset: int) -> list[UserResponse]:
        stmt = select(UserRow).order_by(UserRow.created_at.desc()).limit(limit).offset(offset)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [
            UserResponse(
                id=r.id,
                username=r.username,
                full_name=r.full_name,
                role=UserRole(r.role),
                is_active=r.is_active,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in rows
        ]
