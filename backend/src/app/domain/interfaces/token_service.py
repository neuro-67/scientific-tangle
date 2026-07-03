"""Port for issuing and verifying access/refresh tokens."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


@dataclass(frozen=True, slots=True)
class TokenClaims:
    """Decoded, verified token payload."""

    subject: UUID
    role: str
    type: TokenType
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class IssuedTokens:
    access: str
    refresh: str
    access_expires_at: datetime
    refresh_expires_at: datetime


class ITokenService(ABC):
    """Signs access/refresh JWTs and decodes them back."""

    @abstractmethod
    def issue(self, *, subject: UUID, role: str) -> IssuedTokens: ...

    @abstractmethod
    def decode(self, token: str, *, expected: TokenType) -> TokenClaims: ...
