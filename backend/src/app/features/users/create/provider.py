"""DI provider for the create-user slice."""

from dishka import Provider, Scope, provide

from app.features.users.create.handler import CreateUserHandler
from app.features.users.create.repository import CreateUserRepository


class CreateUserProvider(Provider):
    scope = Scope.REQUEST

    repository = provide(CreateUserRepository)
    handler = provide(CreateUserHandler)
