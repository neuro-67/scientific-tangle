"""Resolve the current user from a bearer token."""

from app.domain.entities.user import User, UserRole
from app.domain.exceptions.auth import (
    ForbiddenError,
    InactiveUserError,
    InvalidTokenError,
)
from app.domain.interfaces.token_service import ITokenService, TokenType
from app.features.shared.auth.repository import CurrentUserRepository


class CurrentUserService:
    def __init__(
        self,
        tokens: ITokenService,
        users: CurrentUserRepository,
    ) -> None:
        self._tokens = tokens
        self._users = users

    async def resolve(self, access_token: str) -> User:
        claims = self._tokens.decode(access_token, expected=TokenType.ACCESS)
        user = await self._users.get_by_id(claims.subject)
        if user is None:
            raise InvalidTokenError("subject not found")
        if not user.is_active:
            raise InactiveUserError("user is deactivated")
        return user

    @staticmethod
    def require_role(user: User, *allowed: UserRole) -> None:
        if user.role not in allowed:
            raise ForbiddenError(f"requires one of: {', '.join(r.value for r in allowed)}")
