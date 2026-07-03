"""Base entity with id and timestamps."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.clock import now_utc


@dataclass(kw_only=True)
class BaseEntity:
    """Common shape for aggregate roots and entities."""

    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = field(default_factory=now_utc)

    def touch(self) -> None:
        self.updated_at = now_utc()
