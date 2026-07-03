"""Base entity: identity, timestamps and domain-event recording."""

import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.domain.clock import now_utc
from app.domain.events.base import DomainEvent


def uuid7() -> UUID:
    """Generate a time-sortable UUIDv7 (RFC 9562).

    The high 48 bits hold a Unix-millisecond timestamp, so IDs sort by creation
    order — useful for index locality and cursor pagination.
    """
    unix_ms = int(time.time() * 1000) & ((1 << 48) - 1)
    rand_a = secrets.randbits(12)
    rand_b = secrets.randbits(62)
    value = (unix_ms << 80) | (0x7 << 76) | (rand_a << 64) | (0b10 << 62) | rand_b
    return UUID(int=value)


@dataclass(kw_only=True)
class BaseEntity:
    """Common base for aggregate roots and entities.

    Persistence-ignorant: carries no ORM metadata. Mapping to storage lives in
    the infrastructure layer.
    """

    id: UUID = field(default_factory=uuid7)
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = field(default_factory=now_utc)
    _pending_events: list[DomainEvent] = field(
        default_factory=list, init=False, repr=False, compare=False
    )

    def touch(self) -> None:
        """Bump ``updated_at`` after a state change."""
        self.updated_at = now_utc()

    def record(self, event: DomainEvent) -> None:
        """Record a domain event raised by a state transition."""
        self._events().append(event)

    def collect_events(self) -> list[DomainEvent]:
        """Return and clear the events recorded since the last collection."""
        events = self._events()
        self._pending_events = []
        return events

    def _events(self) -> list[DomainEvent]:
        # Instances loaded by the ORM bypass __init__, so initialise lazily.
        if not hasattr(self, "_pending_events"):
            self._pending_events = []
        return self._pending_events
