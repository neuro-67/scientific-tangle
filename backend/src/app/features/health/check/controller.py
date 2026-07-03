"""HTTP transport for the health-check use case."""

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, status

from app.features.health.check.handler import HealthCheckHandler
from app.features.health.check.schemas import HealthCheckQuery, HealthCheckResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
)
@inject
async def health_check(
    handler: FromDishka[HealthCheckHandler],
) -> HealthCheckResponse:
    return await handler(HealthCheckQuery())
