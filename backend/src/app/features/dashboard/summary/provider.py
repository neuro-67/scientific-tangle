"""DI provider for the dashboard-summary slice."""

from dishka import Provider, Scope, provide

from app.features.dashboard.summary.handler import DashboardSummaryHandler


class DashboardSummaryProvider(Provider):
    """Wires the dashboard-summary handler. Its Neo4j AsyncDriver dependency
    is provided by Neo4jProvider (already registered for query/ask)."""

    scope = Scope.REQUEST

    handler = provide(DashboardSummaryHandler)
