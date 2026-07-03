"""Aggregated DI providers — the only place that lists every slice provider."""

from dishka import Provider

from app.features.auth.login.provider import LoginProvider
from app.features.auth.refresh.provider import RefreshProvider
from app.features.health.check.provider import HealthCheckProvider
from app.features.shared.auth.provider import CurrentUserProvider
from app.features.users.create.provider import CreateUserProvider
from app.features.users.list.provider import ListUsersProvider
from app.infrastructure.providers.database import DatabaseProvider
from app.infrastructure.providers.security import SecurityProvider

PROVIDERS: list[Provider] = [
    DatabaseProvider(),
    SecurityProvider(),
    CurrentUserProvider(),
    HealthCheckProvider(),
    LoginProvider(),
    RefreshProvider(),
    CreateUserProvider(),
    ListUsersProvider(),
]
