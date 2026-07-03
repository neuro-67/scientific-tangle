"""Auth-related domain exceptions."""

from app.domain.exceptions.base import DomainError


class InvalidUsernameError(DomainError):
    """Username string violates length/format invariant."""


class WeakPasswordError(DomainError):
    """Password does not meet the minimum-strength invariant."""


class InvalidCredentialsError(DomainError):
    """Username/password combination did not authenticate."""


class InactiveUserError(DomainError):
    """User is disabled and cannot authenticate."""


class InvalidTokenError(DomainError):
    """JWT could not be verified or has expired."""


class ForbiddenError(DomainError):
    """Authenticated user lacks the required role."""
