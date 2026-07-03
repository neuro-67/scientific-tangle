"""Port for enqueuing background jobs onto the ingestion worker."""

from abc import ABC, abstractmethod
from uuid import UUID


class IJobQueue(ABC):
    """Hands work off to background workers, decoupled from the caller."""

    @abstractmethod
    async def enqueue_document_processing(self, document_id: UUID) -> None:
        """Schedule ingestion of a stored document."""
