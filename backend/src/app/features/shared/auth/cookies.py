"""Set-Cookie / clear-cookie helpers for the auth token pair."""

from datetime import datetime

from fastapi import Response

from app.domain.interfaces.token_service import IssuedTokens
from app.infrastructure.config.settings import CookieSettings


def set_auth_cookies(
    response: Response,
    tokens: IssuedTokens,
    settings: CookieSettings,
) -> None:
    """Attach httpOnly access + refresh cookies to the response."""
    response.set_cookie(
        key=settings.access_name,
        value=tokens.access,
        expires=_seconds_until(tokens.access_expires_at),
        path="/",
        domain=settings.domain,
        httponly=True,
        secure=settings.secure,
        samesite=settings.samesite,
    )
    response.set_cookie(
        key=settings.refresh_name,
        value=tokens.refresh,
        expires=_seconds_until(tokens.refresh_expires_at),
        path=settings.refresh_path,
        domain=settings.domain,
        httponly=True,
        secure=settings.secure,
        samesite=settings.samesite,
    )


def clear_auth_cookies(response: Response, settings: CookieSettings) -> None:
    response.delete_cookie(
        settings.access_name, path="/", domain=settings.domain
    )
    response.delete_cookie(
        settings.refresh_name, path=settings.refresh_path, domain=settings.domain
    )


def _seconds_until(when: datetime) -> int:
    from app.domain.clock import now_utc

    return max(1, int((when - now_utc()).total_seconds()))
