"""Domain exceptions for the document aggregate."""

from uuid import UUID

from app.domain.exceptions.base import DomainError


class DocumentNotFoundError(DomainError):
    """A document with the requested id does not exist."""

    def __init__(self, document_id: UUID) -> None:
        super().__init__(f"document {document_id} not found")
        self.document_id = document_id


class DocumentStateError(DomainError):
    """A document lifecycle transition was requested from an illegal state."""

    def __init__(self, document_id: UUID, current: object, target: object) -> None:
        super().__init__(
            f"document {document_id} cannot move from {current} to {target}"
        )
        self.document_id = document_id
