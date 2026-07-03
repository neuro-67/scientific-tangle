"""Username value object."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.exceptions.auth import InvalidUsernameError

MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 64


@dataclass(frozen=True, slots=True)
class Username:
    """Normalized login identifier.

    Invariants:
        - lowercased, trimmed
        - length within [MIN_USERNAME_LENGTH, MAX_USERNAME_LENGTH]
    """

    value: str

    def __post_init__(self) -> None:
        if not (MIN_USERNAME_LENGTH <= len(self.value) <= MAX_USERNAME_LENGTH):
            raise InvalidUsernameError(
                f"username length must be {MIN_USERNAME_LENGTH}..{MAX_USERNAME_LENGTH}"
            )

    @classmethod
    def parse(cls, raw: str) -> Username:
        return cls(raw.strip().lower())
