"""HTTP transport for the login use case (JSON body, tokens via Set-Cookie)."""

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Response, status

from app.features.auth.login.handler import LoginHandler
from app.features.auth.login.schemas import LoginCommand
from app.features.auth.schemas import SessionResponse
from app.features.shared.auth.cookies import set_auth_cookies
from app.infrastructure.config.settings import CookieSettings
from app.infrastructure.errors.schemas import ErrorResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Log in",
    description="Sets httpOnly `st_access` and `st_refresh` cookies. Body returns only expiries.",
    responses={401: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
@inject
async def login(
    command: LoginCommand,
    response: Response,
    handler: FromDishka[LoginHandler],
    cookies: FromDishka[CookieSettings],
) -> SessionResponse:
    issued = await handler(command)
    set_auth_cookies(response, issued, cookies)
    return SessionResponse(
        access_expires_at=issued.access_expires_at,
        refresh_expires_at=issued.refresh_expires_at,
    )
