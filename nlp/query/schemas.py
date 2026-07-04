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

    @field_validator("operator", mode="before")
    @classmethod
    def _coerce_strict_inequality(cls, value: object) -> object:
        """The prompt asks for <=/>=/=/range only, but confirmed on a real
        query ("концентрации сульфатов <200 мг/л", the case spec's own
        example phrasing) that the model sometimes writes the literal
        strict "<"/">" from the question anyway. That previously raised a
        ValidationError which silently discarded the whole numeric
        constraint (QuerySpecParser.parse() falls back to the rule-based
        parser, which doesn't extract numeric constraints at all). At this
        domain's reporting precision the </<=  distinction isn't
        meaningful, so coerce instead of dropping the constraint."""
        if value == "<":
            return "<="
        if value == ">":
            return ">="
        return value


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


_FOREIGN_MARKERS = ("мировой", "мировая", "мировую", "зарубежн", "иностран", "foreign", "world", "международн")
_DOMESTIC_MARKERS = ("отечественн", "росси", " рф ", "рф,", "рф.", "domestic", "russia")


def _is_geography_compare(spec: QuerySpec) -> bool:
    if not spec.compare:
        return False
    compare_lower = f" {spec.compare.lower()} "
    return any(m in compare_lower for m in _FOREIGN_MARKERS + _DOMESTIC_MARKERS)


def build_compare_specs(spec: QuerySpec) -> tuple[QuerySpec, QuerySpec] | None:
    """Split a compare-intent QuerySpec into one QuerySpec per side, so
    retrieval runs separately for each side instead of a single unscoped
    query that synthesis then has to somehow untangle into two groups
    (case-specification.md: "«отечественная практика» vs «мировая практика»",
    "«вариант А» vs «вариант Б»"). Returns None when there's nothing to split
    (not a compare intent, or no `compare` value parsed).
    """
    if spec.intent != QueryIntent.COMPARE or not spec.compare:
        return None

    if _is_geography_compare(spec):
        compare_lower = f" {spec.compare.lower()} "
        b_geography = (
            Geography.FOREIGN if any(m in compare_lower for m in _FOREIGN_MARKERS) else Geography.RU
        )
        a_geography = (
            spec.geography
            if spec.geography != Geography.ANY
            else (Geography.RU if b_geography == Geography.FOREIGN else Geography.FOREIGN)
        )
        side_a = spec.model_copy(update={"geography": a_geography})
        side_b = spec.model_copy(update={"geography": b_geography})
        return side_a, side_b

    # Entity-axis compare ("вариант А" vs "вариант Б"): swap the compare value
    # into whichever entity field is already populated, so side B targets the
    # alternate named variant instead of duplicating side A's query.
    for field in ("topics", "processes", "materials", "conditions", "equipment"):
        if getattr(spec, field):
            side_b = spec.model_copy(update={field: [spec.compare]})
            return spec, side_b

    return None


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
