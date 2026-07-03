"""DI wiring for the current-user capability."""

from dishka import Provider, Scope, provide

from app.features.shared.auth.repository import CurrentUserRepository
from app.features.shared.auth.service import CurrentUserService


class CurrentUserProvider(Provider):
    scope = Scope.REQUEST

    repository = provide(CurrentUserRepository)
    service = provide(CurrentUserService)
