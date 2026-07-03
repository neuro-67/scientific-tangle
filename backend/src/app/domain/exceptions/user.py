"""User-management domain exceptions."""

from app.domain.exceptions.base import DomainError


class UserAlreadyExistsError(DomainError):
    """Email is already taken."""


class UserNotFoundError(DomainError):
    """Lookup by id or email produced no user."""
