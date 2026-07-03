"""List users use case (read slice)."""

from dataclasses import dataclass

from app.features.users.list.repository import ListUsersRepository
from app.features.users.schemas import UserResponse


@dataclass(frozen=True, slots=True)
class ListUsersQuery:
    limit: int = 50
    offset: int = 0


class ListUsersHandler:
    def __init__(self, users: ListUsersRepository) -> None:
        self._users = users

    async def __call__(self, query: ListUsersQuery) -> list[UserResponse]:
        return await self._users.list_all(limit=query.limit, offset=query.offset)
