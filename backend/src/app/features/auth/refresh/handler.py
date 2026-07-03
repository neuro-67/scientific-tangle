"""Refresh use case: issue a new token pair from a valid refresh token."""

from dataclasses import dataclass

from app.domain.exceptions.auth import InactiveUserError, InvalidTokenError
from app.domain.interfaces.token_service import IssuedTokens, ITokenService, TokenType
from app.features.auth.refresh.repository import RefreshRepository


@dataclass(frozen=True, slots=True)
class RefreshCommand:
    refresh_token: str


class RefreshHandler:
    def __init__(self, users: RefreshRepository, tokens: ITokenService) -> None:
        self._users = users
        self._tokens = tokens

    async def __call__(self, command: RefreshCommand) -> IssuedTokens:
        claims = self._tokens.decode(command.refresh_token, expected=TokenType.REFRESH)
        user = await self._users.get_by_id(claims.subject)
        if user is None:
            raise InvalidTokenError("subject not found")
        if not user.is_active:
            raise InactiveUserError()

        return self._tokens.issue(subject=user.id, role=user.role.value)
