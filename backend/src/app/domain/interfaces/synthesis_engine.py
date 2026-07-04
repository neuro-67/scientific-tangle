"""Domain port for synthesis engine."""

from abc import ABC, abstractmethod
from typing import Any

from nlp.query.schemas import SynthesisResponse


class ISynthesisEngine(ABC):
    """Generate a structured answer from retrieved findings and a user question."""

    @abstractmethod
    def synthesize(self, question: str, findings: list[dict[str, Any]]) -> SynthesisResponse:
        """Synthesize a structured answer."""
