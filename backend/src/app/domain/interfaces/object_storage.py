"""Port for object (blob) storage of uploaded document bytes."""

from abc import ABC, abstractmethod


class IObjectStorage(ABC):
    """Stores and retrieves opaque binary objects by key."""

    @abstractmethod
    async def put(self, key: str, data: bytes, content_type: str) -> None:
        """Store ``data`` under ``key``, overwriting any existing object."""

    @abstractmethod
    async def get(self, key: str) -> bytes:
        """Retrieve the bytes stored under ``key``."""
