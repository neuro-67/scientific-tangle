"""Exceptions raised by the MinIO object-storage adapter."""

from app.domain.exceptions.base import InfrastructureError


class ObjectStorageError(InfrastructureError):
    """The object store could not complete a requested operation."""
