"""FastAPI dependencies that resolve the current user + enforce roles."""

from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import Cookie, Depends

from app.domain.entities.user import User, UserRole
from app.domain.exceptions.auth import InvalidTokenError
from app.features.shared.auth.service import CurrentUserService
from app.infrastructure.config.settings import get_settings


def _access_cookie_name() -> str:
    return get_settings().cookies.access_name


@inject
async def get_current_user(
    service: FromDishka[CurrentUserService],
    st_access: Annotated[
        str | None,
        Cookie(alias=_access_cookie_name(), include_in_schema=False),
    ] = None,
) -> User:
    if not st_access:
        raise InvalidTokenError("missing access cookie")
    return await service.resolve(st_access)


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*allowed: UserRole) -> Callable[..., Coroutine[Any, Any, User]]:
    """Dependency factory: 403 unless the current user has one of the allowed roles."""

    @inject
    async def _dep(
        user: CurrentUser,
        service: FromDishka[CurrentUserService],
    ) -> User:
        service.require_role(user, *allowed)
        return user

    return _dep


require_admin = require_roles(UserRole.ADMIN)
