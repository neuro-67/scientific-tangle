"""DI provider for the list-users slice."""

from dishka import Provider, Scope, provide

from app.features.users.list.handler import ListUsersHandler
from app.features.users.list.repository import ListUsersRepository


class ListUsersProvider(Provider):
    scope = Scope.REQUEST

    repository = provide(ListUsersRepository)
    handler = provide(ListUsersHandler)
