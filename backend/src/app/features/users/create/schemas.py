"""Create-user DTO."""

from pydantic import BaseModel, ConfigDict, Field

from app.domain.entities.user import UserRole
from app.domain.values.password import MIN_PASSWORD_LENGTH
from app.domain.values.username import MAX_USERNAME_LENGTH, MIN_USERNAME_LENGTH


class CreateUserCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    username: str = Field(min_length=MIN_USERNAME_LENGTH, max_length=MAX_USERNAME_LENGTH)
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=256)
    full_name: str = Field(min_length=1, max_length=255)
    role: UserRole
