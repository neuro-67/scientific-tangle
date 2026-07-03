"""Port for password hashing/verification."""

from abc import ABC, abstractmethod

from app.domain.values.password import HashedPassword, RawPassword


class IPasswordHasher(ABC):
    """Hashes raw passwords and verifies candidates against a stored hash."""

    @abstractmethod
    def hash(self, raw: RawPassword) -> HashedPassword: ...

    @abstractmethod
    def verify(self, raw: RawPassword, hashed: HashedPassword) -> bool: ...
