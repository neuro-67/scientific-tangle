"""HTTP transport for the refresh use case (refresh cookie in, Set-Cookie out)."""

from typing import Annotated

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Cookie, Response, status

from app.domain.exceptions.auth import InvalidTokenError
from app.features.auth.refresh.handler import RefreshCommand, RefreshHandler
from app.features.auth.schemas import SessionResponse
from app.features.shared.auth.cookies import set_auth_cookies
from app.infrastructure.config.settings import CookieSettings, get_settings
from app.infrastructure.errors.schemas import ErrorResponse


def _refresh_cookie_name() -> str:
    return get_settings().cookies.refresh_name


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/refresh",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh session",
    description="Reads the `st_refresh` cookie and re-issues both cookies.",
    responses={401: {"model": ErrorResponse}},
)
@inject
async def refresh(
    response: Response,
    handler: FromDishka[RefreshHandler],
    cookies: FromDishka[CookieSettings],
    st_refresh: Annotated[
        str | None,
        Cookie(alias=_refresh_cookie_name(), include_in_schema=False),
    ] = None,
) -> SessionResponse:
    if not st_refresh:
        raise InvalidTokenError("missing refresh cookie")
    issued = await handler(RefreshCommand(refresh_token=st_refresh))
    set_auth_cookies(response, issued, cookies)
    return SessionResponse(
        access_expires_at=issued.access_expires_at,
        refresh_expires_at=issued.refresh_expires_at,
    )
