"""Login DTO."""

from pydantic import BaseModel, ConfigDict, Field


class LoginCommand(BaseModel):
    """Credentials sent as a JSON body to POST /auth/login.

    Defaults reference the dev-seeded admin so Swagger's "Try it out" is one click away.
    """

    model_config = ConfigDict(frozen=True)

    username: str = Field(default="admin")
    password: str = Field(default="admin")
