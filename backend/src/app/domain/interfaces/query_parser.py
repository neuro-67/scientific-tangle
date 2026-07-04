"""Domain port for LLM-based query parsing."""

from abc import ABC, abstractmethod

from nlp.query.schemas import QuerySpec


class IQueryParser(ABC):
    """Convert a natural-language question into a structured QuerySpec."""

    @abstractmethod
    def parse(self, question: str) -> QuerySpec:
        """Parse the question; may raise on malformed input or LLM failure."""
