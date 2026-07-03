"""Argon2id-backed password hasher."""

from passlib.context import CryptContext

from app.domain.interfaces.password_hasher import IPasswordHasher
from app.domain.values.password import HashedPassword, RawPassword


class Argon2PasswordHasher(IPasswordHasher):
    """OWASP-recommended memory-hard password hashing."""

    def __init__(self) -> None:
        self._context = CryptContext(schemes=["argon2"], deprecated="auto")

    def hash(self, raw: RawPassword) -> HashedPassword:
        return HashedPassword(self._context.hash(raw.value))

    def verify(self, raw: RawPassword, hashed: HashedPassword) -> bool:
        return bool(self._context.verify(raw.value, hashed.value))
