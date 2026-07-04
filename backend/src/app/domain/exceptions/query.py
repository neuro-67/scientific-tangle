"""Domain exception for query-related failures."""

from app.domain.exceptions.base import DomainError


class QueryParseError(DomainError):
    """The natural-language question could not be parsed into a QuerySpec."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"query parse failed: {reason}")
        self.reason = reason


class GraphSearchError(DomainError):
    """The graph search operation failed."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"graph search failed: {reason}")
        self.reason = reason
