"""JWT-backed token service."""

from datetime import timedelta
from uuid import UUID, uuid4

from jose import JWTError, jwt

from app.domain.clock import now_utc
from app.domain.exceptions.auth import InvalidTokenError
from app.domain.interfaces.token_service import (
    IssuedTokens,
    ITokenService,
    TokenClaims,
    TokenType,
)
from app.infrastructure.config.settings import JwtSettings


class JwtTokenService(ITokenService):
    """Signs and verifies access/refresh JWTs using the configured secret."""

    def __init__(self, settings: JwtSettings) -> None:
        self._settings = settings

    def issue(self, *, subject: UUID, role: str) -> IssuedTokens:
        now = now_utc()
        access_exp = now + timedelta(minutes=self._settings.access_ttl_minutes)
        refresh_exp = now + timedelta(days=self._settings.refresh_ttl_days)
        access = self._encode(subject, role, TokenType.ACCESS, now, access_exp)
        refresh = self._encode(subject, role, TokenType.REFRESH, now, refresh_exp)
        return IssuedTokens(
            access=access,
            refresh=refresh,
            access_expires_at=access_exp,
            refresh_expires_at=refresh_exp,
        )

    def decode(self, token: str, *, expected: TokenType) -> TokenClaims:
        try:
            payload = jwt.decode(
                token,
                self._settings.secret,
                algorithms=[self._settings.algorithm],
            )
        except JWTError as exc:
            raise InvalidTokenError("token could not be verified") from exc

        try:
            token_type = TokenType(payload["type"])
            subject = UUID(payload["sub"])
            role = str(payload["role"])
            exp = payload["exp"]
        except (KeyError, ValueError) as exc:
            raise InvalidTokenError("token payload is malformed") from exc

        if token_type is not expected:
            raise InvalidTokenError(f"expected {expected.value} token")

        from datetime import UTC, datetime

        return TokenClaims(
            subject=subject,
            role=role,
            type=token_type,
            expires_at=datetime.fromtimestamp(exp, tz=UTC),
        )

    def _encode(
        self,
        subject: UUID,
        role: str,
        token_type: TokenType,
        issued_at: object,
        expires_at: object,
    ) -> str:
        payload = {
            "sub": str(subject),
            "role": role,
            "type": token_type.value,
            "iat": int(issued_at.timestamp()),  # type: ignore[attr-defined]
            "exp": int(expires_at.timestamp()),  # type: ignore[attr-defined]
            "jti": str(uuid4()),
        }
        return jwt.encode(payload, self._settings.secret, algorithm=self._settings.algorithm)
