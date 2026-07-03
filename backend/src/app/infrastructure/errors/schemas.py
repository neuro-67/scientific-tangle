"""Uniform error envelope surfaced to API clients."""

from pydantic import BaseModel, ConfigDict, Field


class ErrorResponse(BaseModel):
    """Every non-2xx response body has this shape.

    - `message` — short machine-readable code (`invalid_credentials`, `forbidden`, ...)
    - `detail`  — optional list of human-readable strings with additional context
    """

    model_config = ConfigDict(frozen=True)

    message: str = Field(examples=["forbidden"])
    detail: list[str] | None = Field(default=None, examples=[["insufficient role"]])
