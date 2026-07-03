"""DI provider for the refresh slice."""

from dishka import Provider, Scope, provide

from app.features.auth.refresh.handler import RefreshHandler
from app.features.auth.refresh.repository import RefreshRepository


class RefreshProvider(Provider):
    scope = Scope.REQUEST

    repository = provide(RefreshRepository)
    handler = provide(RefreshHandler)
