"""Aggregated DI providers — the only place that lists every slice provider."""

from dishka import Provider

from app.features.health.check.provider import HealthCheckProvider

PROVIDERS: list[Provider] = [
    HealthCheckProvider(),
]
