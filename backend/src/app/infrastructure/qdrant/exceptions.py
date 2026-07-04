"""Exceptions raised by the Qdrant vector-search adapter."""

from app.domain.exceptions.base import InfrastructureError


class VectorSearchError(InfrastructureError):
    """The vector store could not complete a requested operation."""
