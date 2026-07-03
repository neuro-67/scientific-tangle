"""DI wiring for the password hasher and token service."""

from dishka import Provider, Scope, provide

from app.domain.interfaces.password_hasher import IPasswordHasher
from app.domain.interfaces.token_service import ITokenService
from app.infrastructure.config.settings import AppSettings, CookieSettings, JwtSettings
from app.infrastructure.security.password_hasher import Argon2PasswordHasher
from app.infrastructure.security.token_service import JwtTokenService


class SecurityProvider(Provider):
    scope = Scope.APP

    @provide
    def jwt_settings(self, settings: AppSettings) -> JwtSettings:
        return settings.jwt

    @provide
    def cookie_settings(self, settings: AppSettings) -> CookieSettings:
        return settings.cookies

    @provide
    def password_hasher(self) -> IPasswordHasher:
        return Argon2PasswordHasher()

    @provide
    def token_service(self, jwt_settings: JwtSettings) -> ITokenService:
        return JwtTokenService(jwt_settings)
