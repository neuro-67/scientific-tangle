"""Query pipeline for Scientific Tangle.

Parses natural-language questions into structured QuerySpec and will later
drive hybrid retrieval + synthesis.
"""

from nlp.query.schemas import QuerySpec, NumericConstraint, TimeRange, SynthesisResponse, SourceCitation
from nlp.query.parser import QuerySpecParser

__all__ = [
    "QuerySpec",
    "NumericConstraint",
    "TimeRange",
    "SynthesisResponse",
    "SourceCitation",
    "QuerySpecParser",
]
