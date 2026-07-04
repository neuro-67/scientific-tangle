"""Dashboard summary use case: aggregate knowledge-graph coverage/gap/risk
metrics for the management dashboard (case-specification.md "Дашборды для
руководителей").

Read slice: no domain entities, no business decisions -- just projects
Neo4j aggregate queries into response DTOs (docs/backend/ARCHITECTURE.md §5).
"""

from __future__ import annotations

from neo4j import AsyncDriver

from app.features.dashboard.summary.schemas import DashboardSummaryResponse
from nlp.query.retrieval.analytics import dashboard_summary


class DashboardSummaryHandler:
    """Orchestrates the knowledge-base analytics queries for the dashboard."""

    def __init__(self, driver: AsyncDriver) -> None:
        self._driver = driver

    async def __call__(self) -> DashboardSummaryResponse:
        data = await dashboard_summary(self._driver)
        return DashboardSummaryResponse.model_validate(data)
