"""Clear the auth cookies. Idempotent."""

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Response, status

from app.features.shared.auth.cookies import clear_auth_cookies
from app.infrastructure.config.settings import CookieSettings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log out",
    description="Clears the auth cookies.",
)
@inject
async def logout(
    response: Response,
    cookies: FromDishka[CookieSettings],
) -> None:
    clear_auth_cookies(response, cookies)
