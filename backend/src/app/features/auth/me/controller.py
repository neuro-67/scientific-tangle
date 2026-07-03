"""Return the profile of the currently authenticated user."""

from fastapi import APIRouter, status

from app.features.shared.auth.dependencies import CurrentUser
from app.features.users.schemas import UserResponse
from app.infrastructure.errors.schemas import ErrorResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Current user",
    responses={401: {"model": ErrorResponse}},
)
async def me(user: CurrentUser) -> UserResponse:
    return UserResponse.from_domain(user)
