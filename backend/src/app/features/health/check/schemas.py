"""DTOs for the health-check use case."""

from datetime import datetime

from pydantic import BaseModel


class HealthCheckQuery(BaseModel):
    """Empty query — health-check takes no input."""


class HealthCheckResponse(BaseModel):
    """Liveness signal returned by the health-check endpoint."""

    status: str
    timestamp: datetime
