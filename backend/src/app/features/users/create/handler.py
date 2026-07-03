"""Admin-only use case: create a new user."""

from app.domain.entities.user import User
from app.domain.exceptions.user import UserAlreadyExistsError
from app.domain.interfaces.password_hasher import IPasswordHasher
from app.domain.values.password import RawPassword
from app.domain.values.username import Username
from app.features.users.create.repository import CreateUserRepository
from app.features.users.create.schemas import CreateUserCommand
from app.features.users.schemas import UserResponse


class CreateUserHandler:
    def __init__(self, users: CreateUserRepository, hasher: IPasswordHasher) -> None:
        self._users = users
        self._hasher = hasher

    async def __call__(self, command: CreateUserCommand) -> UserResponse:
        username = Username.parse(command.username)
        raw = RawPassword(command.password)

        if await self._users.exists_by_username(username.value):
            raise UserAlreadyExistsError(username.value)

        user = User.create(
            username=username,
            hashed_password=self._hasher.hash(raw),
            role=command.role,
            full_name=command.full_name,
        )
        await self._users.add(user)
        return UserResponse.from_domain(user)
