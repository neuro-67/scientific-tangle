"""Health-check use case: returns a liveness signal."""

from app.domain.clock import now_utc
from app.features.health.check.schemas import HealthCheckQuery, HealthCheckResponse


class HealthCheckHandler:
    """Returns an 'ok' signal with the current UTC time."""

    async def __call__(self, query: HealthCheckQuery) -> HealthCheckResponse:
        return HealthCheckResponse(status="ok", timestamp=now_utc())
