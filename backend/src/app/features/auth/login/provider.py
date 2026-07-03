"""DI provider for the login slice."""

from dishka import Provider, Scope, provide

from app.features.auth.login.handler import LoginHandler
from app.features.auth.login.repository import LoginRepository


class LoginProvider(Provider):
    scope = Scope.REQUEST

    repository = provide(LoginRepository)
    handler = provide(LoginHandler)
