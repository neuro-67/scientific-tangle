"""Root of the domain event hierarchy."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DomainEvent:
    """Immutable record of a fact that happened in the domain (past tense)."""
