"""Login use case: exchange username+password for a fresh token pair."""

from app.domain.exceptions.auth import InactiveUserError, InvalidCredentialsError
from app.domain.interfaces.password_hasher import IPasswordHasher
from app.domain.interfaces.token_service import ITokenService, IssuedTokens
from app.domain.values.password import RawPassword
from app.features.auth.login.repository import LoginRepository
from app.features.auth.login.schemas import LoginCommand


class LoginHandler:
    def __init__(
        self,
        users: LoginRepository,
        hasher: IPasswordHasher,
        tokens: ITokenService,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._tokens = tokens

    async def __call__(self, command: LoginCommand) -> IssuedTokens:
        # Login normalizes the identifier but does not enforce Username invariants —
        # seeded dev users (e.g. `admin`) must be able to sign in.
        identifier = command.username.strip().lower()
        user = await self._users.find_by_username(identifier)
        if user is None:
            raise InvalidCredentialsError()

        candidate = RawPassword.__new__(RawPassword)
        object.__setattr__(candidate, "value", command.password)
        if not self._hasher.verify(candidate, user.hashed_password):
            raise InvalidCredentialsError()

        if not user.is_active:
            raise InactiveUserError()

        return self._tokens.issue(subject=user.id, role=user.role.value)
