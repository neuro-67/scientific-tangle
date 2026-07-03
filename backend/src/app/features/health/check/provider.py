"""DI provider for the health-check slice."""

from dishka import Provider, Scope, provide

from app.features.health.check.handler import HealthCheckHandler


class HealthCheckProvider(Provider):
    """Wires the health-check handler."""

    scope = Scope.REQUEST
    handler = provide(HealthCheckHandler)
