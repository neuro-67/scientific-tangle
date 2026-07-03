"""Root of the domain exception hierarchy."""


class AppError(Exception):
    """Base class for all application errors."""


class DomainError(AppError):
    """Business-rule violation raised by the domain layer."""


class InfrastructureError(AppError):
    """Failure raised by adapters/integrations."""
