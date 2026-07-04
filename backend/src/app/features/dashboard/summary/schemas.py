"""Response DTOs for the management dashboard summary.

Read slice (docs/backend/ARCHITECTURE.md §5): projects Neo4j aggregate rows
straight into response DTOs, no domain entities, no business decisions.
"""

from __future__ import annotations

from pydantic import BaseModel


class DomainCoverage(BaseModel):
    domain: str
    n_processes: int
    n_publications: int


class KnowledgeGap(BaseModel):
    material: str
    process: str
    condition: str


class GeographyOnlyTopic(BaseModel):
    entity: str
    type: str
    only_geography: str


class LowSourceEntity(BaseModel):
    entity: str
    type: str
    source_count: int


class ContradictionPair(BaseModel):
    node_a: str
    type_a: str
    source_a: str | None
    node_b: str
    type_b: str
    source_b: str | None


class DisputedValue(BaseModel):
    """A CONTRADICTS pair enriched with the two conflicting measured values."""

    node_a: str
    type_a: str
    source_a: str | None
    node_b: str
    type_b: str
    source_b: str | None
    disputed_property: str | None = None
    value_a: float | None = None
    value_b: float | None = None
    unit: str | None = None


class KnowledgeChange(BaseModel):
    """A fact whose value/confidence changed when a newer source was ingested."""

    fact: str
    type: str
    previous_value: float | str | None = None
    current_value: float | str | None = None
    unit: str | None = None
    changed_at: str | None = None
    superseded_by: str | None = None


class DashboardSummaryResponse(BaseModel):
    """case-specification.md 'Дашборды для руководителей':
    метрики покрытия знаний по направлениям + зоны риска.

    Team activity is NOT included -- it requires an audit log, which does
    not exist yet (docs/backend/AUTH.md already flags this as missing).
    """

    coverage_by_domain: list[DomainCoverage]
    gaps: list[KnowledgeGap]
    geography_only_topics: list[GeographyOnlyTopic]
    risk_low_sources: list[LowSourceEntity]
    risk_contradictions: list[ContradictionPair]
    # Проактивный радар противоречий с конфликтующими значениями, и таймлайн
    # эволюции фактов (обе фичи graph-native, невозможны в чистом RAG).
    contradiction_radar: list[DisputedValue] = []
    knowledge_evolution: list[KnowledgeChange] = []
