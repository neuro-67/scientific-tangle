"""HTTP transport for creating users (admin-only)."""

from typing import Annotated

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, status

from app.domain.entities.user import User
from app.features.shared.auth.dependencies import require_admin
from app.features.users.create.handler import CreateUserHandler
from app.features.users.create.schemas import CreateUserCommand
from app.features.users.schemas import UserResponse
from app.infrastructure.errors.schemas import ErrorResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description="Admin-only. Creates a user with the given role and returns the created record.",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
@inject
async def create_user(
    command: CreateUserCommand,
    handler: FromDishka[CreateUserHandler],
    _admin: Annotated[User, Depends(require_admin)],
) -> UserResponse:
    return await handler(command)
