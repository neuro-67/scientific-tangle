"""HTTP transport for listing users (admin-only)."""

from typing import Annotated

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, Query, status

from app.domain.entities.user import User
from app.features.shared.auth.dependencies import require_admin
from app.features.users.list.handler import ListUsersHandler, ListUsersQuery
from app.features.users.schemas import UserResponse
from app.infrastructure.errors.schemas import ErrorResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "",
    response_model=list[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="List users",
    description="Admin-only. Paginated list, newest first.",
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
@inject
async def list_users(
    handler: FromDishka[ListUsersHandler],
    _admin: Annotated[User, Depends(require_admin)],
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[UserResponse]:
    return await handler(ListUsersQuery(limit=limit, offset=offset))
