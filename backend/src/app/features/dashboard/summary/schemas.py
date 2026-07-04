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
