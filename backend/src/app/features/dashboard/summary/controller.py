"""HTTP transport for the dashboard-summary use case."""

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, status

from app.features.dashboard.summary.handler import DashboardSummaryHandler
from app.features.dashboard.summary.schemas import DashboardSummaryResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Knowledge-base coverage/gap/risk metrics",
    description="Coverage by domain, unstudied material/process/condition combinations, "
    "RU-only/foreign-only topics, low-source entities, and contradictions.",
)
@inject
async def get_dashboard_summary(
    handler: FromDishka[DashboardSummaryHandler],
) -> DashboardSummaryResponse:
    """Return aggregate knowledge-graph metrics for the management dashboard."""
    return await handler()
