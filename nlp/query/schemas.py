"""Pydantic schemas for the query pipeline.

These DTOs are the contract between the query parser, retrieval layer,
synthesis layer and the backend API.

Mirrors the project ontology (ONTOLOGY.md):
- Node labels: Material, Process, Equipment, Property, Measurement, Condition,
  Experiment, Publication, Expert, Facility, Finding, Source, Topic
- Relationship types: uses_material, applies_to, operates_at_condition,
  has_measurement, measures_property, uses_equipment, produces_output, showed,
  described_in, authored_by, expert_in, conducted_at, validated_by,
  contradicts, supports, tagged, has_source
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class QueryIntent(StrEnum):
    """Question intent taxonomy aligned with the product requirements."""

    SEARCH = "search"
    REVIEW = "review"
    COMPARE = "compare"
    GAP = "gap"


class Geography(StrEnum):
    """Geography filter for sources."""

    RU = "RU"
    FOREIGN = "foreign"
    ANY = "any"


class NumericOperator(StrEnum):
    """Allowed numeric comparison operators."""

    LTE = "<="
    GTE = ">="
    EQ = "="
    RANGE = "range"


class TimeRange(BaseModel):
    """Optional publication-year window."""

    from_year: int | None = Field(None, alias="from")
    to_year: int | None = Field(None, alias="to")

    model_config = {"populate_by_name": True}


class NumericConstraint(BaseModel):
    """A single numeric requirement from the question.

    Maps to Property + Measurement in the ontology.
    For a range both min/max are set and operator is 'range'.
    For a single threshold value is set and operator is '<=', '>=' or '='.
    """

    property: str = Field(description="Canonical property name, e.g. 'сульфаты'")
    operator: Literal["<=", ">=", "=", "range"] = Field(default="<=")
    value: float | None = Field(None, description="Single threshold value")
    min: float | None = Field(None, description="Range lower bound")
    max: float | None = Field(None, description="Range upper bound")
    unit: str | None = Field(None, description="Canonical unit, e.g. 'мг/л'")


class QuerySpec(BaseModel):
    """Structured representation of a user question.

    Mirrors the ontology node labels:
    - Material, Process, Equipment, Property, Condition, Experiment,
      Expert, Facility, Topic

    This is the main contract handed from the query parser to the retrieval
    engine and to the backend orchestrator.
    """

    # --- Core ontology nodes ---
    intent: QueryIntent = Field(default=QueryIntent.REVIEW)

    materials: list[str] = Field(default_factory=list, description="Material canonical names")
    processes: list[str] = Field(default_factory=list, description="Process canonical names")
    equipment: list[str] = Field(default_factory=list, description="Equipment canonical names")
    properties: list[str] = Field(default_factory=list, description="Property names (e.g. концентрация, температура)")
    conditions: list[str] = Field(default_factory=list, description="Condition names (e.g. холодный климат, кучное выщелачивание)")
    experiments: list[str] = Field(default_factory=list, description="Experiment titles")
    experts: list[str] = Field(default_factory=list, description="Expert names")
    facilities: list[str] = Field(default_factory=list, description="Facility/lab names")
    topics: list[str] = Field(default_factory=list, description="Topic/domain tags")

    # --- Publication filters ---
    geography: Geography = Field(default=Geography.ANY, description="RU | foreign | any")
    time_range: TimeRange = Field(default_factory=TimeRange, description="Publication year range")

    # --- Numeric constraints (Property + Measurement) ---
    numeric_constraints: list[NumericConstraint] = Field(default_factory=list)

    # --- Compare intent ---
    compare: str | None = Field(None, description="Second object for compare intent")

    # --- Implicit relationship hints ---
    # When user asks "A for B", we can hint the relationship type
    relation_hint: str | None = Field(
        None,
        description="Inferred relationship: uses_material, applies_to, operates_at_condition, etc."
    )

    @field_validator("materials", "processes", "equipment", "properties", "conditions",
                     "experiments", "experts", "facilities", "topics", mode="before")
    @classmethod
    def _none_to_empty_list(cls, value: list[str] | None) -> list[str]:
        return value if value is not None else []

    @field_validator("time_range", mode="before")
    @classmethod
    def _none_to_empty_timerange(cls, value: dict | None) -> dict:
        return value if value is not None else {}


class SourceCitation(BaseModel):
    """One cited source attached to an answer fragment.

    Верификация знаний (case-specification.md): "указание источника, уровня
    достоверности, даты актуализации" -- `year` is the source's own date
    (publication year); `extracted_at` is the modification/ingestion date
    (when this fact was last written into the graph), i.e. the second of the
    two "актуализация" dates the case spec asks for.
    """

    title: str | None = None
    year: int | None = None
    geography: Geography | None = None
    confidence: Literal["high", "medium", "low"] | None = None
    span: str | None = Field(None, description="Page / offset reference")
    extracted_at: str | None = Field(None, description="Ingestion/modification date (ISO date), not the source's own year")

    @field_validator("year", mode="before")
    @classmethod
    def _coerce_year(cls, value: object) -> object:
        """The LLM sometimes writes a placeholder string ("не указан") instead
        of null when a source has no year -- confirmed on real retrieval data
        (sparse Publication links). Prompting alone doesn't reliably prevent
        this, so fail soft here instead of raising validation errors that
        would silently discard the whole synthesized answer."""
        if isinstance(value, str) and not value.strip().isdigit():
            return None
        return value

    @field_validator("geography", mode="before")
    @classmethod
    def _coerce_geography(cls, value: object) -> object:
        if isinstance(value, str) and value not in ("RU", "foreign", "any"):
            return None
        return value


class SynthesisResponse(BaseModel):
    """Final structured answer produced by the synthesis step."""

    answer: str
    consensus: list[str] = Field(default_factory=list)
    disagreements: list[dict] = Field(default_factory=list)
    sources: list[SourceCitation] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    experts: list[dict] = Field(default_factory=list)
    recommendations: list[dict] = Field(
        default_factory=list,
        description="case-specification.md 'Рекомендации': similar cases from adjacent domains, related topics for further study (experts/teams already covered by `experts`)",
    )
    confidence: Literal["high", "medium", "low"] | None = None
