"""Raw password value object with a minimum-strength invariant."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.exceptions.auth import WeakPasswordError

MIN_PASSWORD_LENGTH = 8


@dataclass(frozen=True, slots=True)
class RawPassword:
    """A cleartext password held only long enough to hash it.

    Invariants:
        - length >= MIN_PASSWORD_LENGTH
        - contains at least one letter and one digit
    """

    value: str

    def __post_init__(self) -> None:
        if len(self.value) < MIN_PASSWORD_LENGTH:
            raise WeakPasswordError(
                f"password must be at least {MIN_PASSWORD_LENGTH} characters"
            )
        if not any(c.isalpha() for c in self.value) or not any(c.isdigit() for c in self.value):
            raise WeakPasswordError("password must contain letters and digits")


@dataclass(frozen=True, slots=True)
class HashedPassword:
    """Opaque hash string produced by the password hasher."""

    value: str
