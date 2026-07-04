"""Knowledge-base analytics for the management dashboard
(case-specification.md "Дашборды для руководителей") and gap detection
(docs/ONTOLOGY.md §7).

Async driver, matching how the rest of the backend accesses Neo4j
(backend/src/app/infrastructure/neo4j/graph_search.py) so this can be wired
into a FastAPI handler via the existing Neo4jProvider without a second,
separate sync connection.
"""

from __future__ import annotations

from typing import Any

from neo4j import AsyncDriver


async def coverage_by_domain(driver: AsyncDriver) -> list[dict[str, Any]]:
    """Entity counts grouped by Process.domain -- "метрики покрытия знаний по направлениям".

    Groups by whatever domain values are actually present in the graph
    rather than hardcoding the case spec's three example domains
    (гидрометаллургия/экология/переработка отходов): those are examples, not
    an exhaustive enum, and a demo corpus may not touch all of them yet.
    """
    query = """
    MATCH (p:Process)
    WHERE p.domain IS NOT NULL
    OPTIONAL MATCH (p)-[:DESCRIBED_IN]->(pub:Publication)
    WITH p.domain AS domain, count(DISTINCT p) AS n_processes, count(DISTINCT pub) AS n_publications
    RETURN domain, n_processes, n_publications
    ORDER BY n_processes DESC
    """
    async with driver.session() as session:
        result = await session.run(query)
        return await result.data()


async def gap_detection(driver: AsyncDriver, limit: int = 50) -> list[dict[str, Any]]:
    """Material x Process x Condition combinations with no linking Experiment.

    docs/ONTOLOGY.md §7 example query didn't actually run as written (mixed
    undefined relation to `p`, duplicate WHERE conditions) -- this is a
    corrected, tested version against the real relation types written by
    nlp/ingestion/neo4j_import.py (UPPER_SNAKE, not lowercase).
    """
    query = """
    MATCH (m:Material), (p:Process), (c:Condition)
    WHERE NOT EXISTS {
        MATCH (e:Experiment)-[:USES_MATERIAL]->(m)
        MATCH (e)-[:OPERATES_AT_CONDITION]->(c)
        MATCH (e)-[:USES_MATERIAL|APPLIES_TO]->()<-[:USES_MATERIAL|APPLIES_TO]-(p)
    }
    RETURN m.id AS material, p.id AS process, c.id AS condition
    LIMIT $limit
    """
    async with driver.session() as session:
        result = await session.run(query, limit=limit)
        return await result.data()


async def geography_only_topics(driver: AsyncDriver) -> list[dict[str, Any]]:
    """Entities described only in RU or only in foreign publications.

    case-specification.md: "Какие технологии описаны только в отечественной
    или только в зарубежной литературе".
    """
    query = """
    MATCH (n)-[:DESCRIBED_IN]->(pub:Publication)
    WHERE pub.geography IS NOT NULL AND (n:Material OR n:Process OR n:Topic)
    WITH n, collect(DISTINCT pub.geography) AS geographies
    WHERE size(geographies) = 1
    RETURN n.id AS entity, labels(n)[0] AS type, geographies[0] AS only_geography
    ORDER BY type, entity
    LIMIT 100
    """
    async with driver.session() as session:
        result = await session.run(query)
        return await result.data()


async def risk_zones_low_sources(driver: AsyncDriver, max_sources: int = 1) -> list[dict[str, Any]]:
    """Entities backed by <= max_sources publications -- "зоны риска: темы с
    малым количеством источников"."""
    query = """
    MATCH (n)
    WHERE n:Material OR n:Process OR n:Topic OR n:Equipment
    OPTIONAL MATCH (n)-[:DESCRIBED_IN]->(pub:Publication)
    WITH n, count(DISTINCT pub) AS source_count
    WHERE source_count <= $max_sources
    RETURN n.id AS entity, labels(n)[0] AS type, source_count
    ORDER BY source_count ASC, entity
    LIMIT 100
    """
    async with driver.session() as session:
        result = await session.run(query, max_sources=max_sources)
        return await result.data()


async def risk_zones_contradictions(driver: AsyncDriver) -> list[dict[str, Any]]:
    """Node pairs with a CONTRADICTS edge -- "зоны риска: противоречивые данные".

    docs/ONTOLOGY.md documents contradicts as Finding->Finding, but real
    extraction applies it between whatever node types are contextually
    conflicting (confirmed on real data: Experiment<->Experiment,
    Process<->Process, Finding<->Topic all occur) -- not restricted to
    Finding here, or this silently misses real contradictions.
    """
    query = """
    MATCH (a)-[:CONTRADICTS]->(b)
    OPTIONAL MATCH (a)-[:DESCRIBED_IN]->(pub_a:Publication)
    OPTIONAL MATCH (b)-[:DESCRIBED_IN]->(pub_b:Publication)
    RETURN a.id AS node_a, labels(a)[0] AS type_a, pub_a.id AS source_a,
           b.id AS node_b, labels(b)[0] AS type_b, pub_b.id AS source_b
    LIMIT 100
    """
    async with driver.session() as session:
        result = await session.run(query)
        return await result.data()


async def fact_history(driver: AsyncDriver, fact_id: str) -> list[dict[str, Any]]:
    """Prior versions of a Measurement/Finding, most recent first.

    case-specification.md: "Версионирование фактов: отслеживание изменений в
    выводах, обновление данных при появлении новых источников". Written by
    nlp/ingestion/neo4j_import.py's _archive_previous_version() whenever a
    re-import changes a fact's value/confidence instead of just overwriting
    it (MERGE is otherwise last-write-wins with no history kept).
    """
    query = """
    MATCH (rev:Revision)-[:REVISION_OF]->(n {id: $fact_id})
    RETURN rev.superseded_at AS superseded_at, rev.superseded_by_document AS superseded_by_document,
           apoc.map.removeKeys(properties(rev), ['superseded_at', 'superseded_by_document']) AS previous_properties
    ORDER BY rev.superseded_at DESC
    """
    async with driver.session() as session:
        result = await session.run(query, fact_id=fact_id)
        return await result.data()


async def recommend_experts(
    driver: AsyncDriver, entity_names: list[str], limit: int = 10
) -> list[dict[str, Any]]:
    """Experts/labs who have worked on the queried entities.

    case-specification.md: "кто в организации является носителем экспертизы".
    Reaches experts two ways -- authors of publications that describe the
    queried materials/processes/topics, and experts explicitly tagged
    EXPERT_IN one of the queried topics -- and ranks by how many of the query
    entities each one touches, so the most relevant person floats to the top.
    This is the institutional-memory answer plain vector RAG can't give: it
    needs the who-authored-what graph, not similar text.
    """
    query = """
    UNWIND $names AS name
    MATCH (n {id: name})
    OPTIONAL MATCH (n)-[:DESCRIBED_IN]->(pub:Publication)-[:AUTHORED_BY]->(author:Expert)
    OPTIONAL MATCH (n)<-[:EXPERT_IN]-(topical:Expert)
    OPTIONAL MATCH (n)-[:VALIDATED_BY]->(validator:Expert)
    WITH name, collect(DISTINCT author) + collect(DISTINCT topical) + collect(DISTINCT validator) AS experts
    UNWIND experts AS e
    WITH e, count(DISTINCT name) AS relevance
    WHERE e IS NOT NULL AND coalesce(e.stub, false) = false
    OPTIONAL MATCH (e)-[:CONDUCTED_AT|EXPERT_IN]->(ctx)
    OPTIONAL MATCH (pub2:Publication)-[:AUTHORED_BY]->(e)
    RETURN e.id AS expert,
           relevance,
           e.email AS email,
           count(DISTINCT pub2) AS n_publications,
           collect(DISTINCT ctx.id)[..3] AS context
    ORDER BY relevance DESC, n_publications DESC
    LIMIT $limit
    """
    async with driver.session() as session:
        result = await session.run(query, names=entity_names, limit=limit)
        return await result.data()


async def knowledge_evolution(driver: AsyncDriver, limit: int = 50) -> list[dict[str, Any]]:
    """Global timeline of facts that changed when a newer source was ingested.

    case-specification.md: "отслеживание изменений в выводах, обновление данных
    при появлении новых источников". This is the corpus-wide view of the
    per-fact history in fact_history(): every :Revision snapshot, newest first,
    with the old vs current value and which document superseded it. Unique to
    this system -- it exists only because ingestion versions facts instead of
    overwriting them.
    """
    query = """
    MATCH (rev:Revision)-[:REVISION_OF]->(n)
    RETURN n.id AS fact,
           labels(n)[0] AS type,
           rev.value AS previous_value,
           n.value AS current_value,
           rev.unit AS unit,
           rev.superseded_at AS changed_at,
           rev.superseded_by_document AS superseded_by
    ORDER BY rev.superseded_at DESC
    LIMIT $limit
    """
    async with driver.session() as session:
        result = await session.run(query, limit=limit)
        return await result.data()


async def provenance_path(driver: AsyncDriver, fact_id: str) -> dict[str, Any]:
    """Full trust chain behind a single fact, for the 'why do we believe this'
    view (case-specification.md verification model: источник + достоверность +
    дата актуализации).

    Surfaces the provenance the graph already carries but nothing displayed:
    the confidence, the Source span(s), whether each linked measurement was
    mechanically verified against the raw document text (Measurement.verified),
    the publication + its authors, and any expert who validated it.
    """
    query = """
    MATCH (f {id: $fact_id})
    OPTIONAL MATCH (f)-[:HAS_SOURCE]->(src:Source)
    OPTIONAL MATCH (f)-[:HAS_MEASUREMENT]->(m:Measurement)
    OPTIONAL MATCH (f)-[:DESCRIBED_IN]->(pub:Publication)
    OPTIONAL MATCH (pub)-[:AUTHORED_BY]->(author:Expert)
    OPTIONAL MATCH (f)-[:VALIDATED_BY]->(validator:Expert)
    RETURN f.id AS fact,
           labels(f)[0] AS type,
           f.confidence AS confidence,
           f.source_document AS source_document,
           f.ingestion_date AS extracted_at,
           collect(DISTINCT src.span) AS source_spans,
           collect(DISTINCT {value: m.value, min: m.min, max: m.max, unit: m.unit,
                             verified: m.verified}) AS measurements,
           collect(DISTINCT pub.id) AS publications,
           collect(DISTINCT author.id) AS authors,
           collect(DISTINCT validator.id) AS validated_by
    """
    async with driver.session() as session:
        result = await session.run(query, fact_id=fact_id)
        record = await result.single()
        return dict(record) if record else {}


async def contradiction_radar(driver: AsyncDriver, limit: int = 50) -> list[dict[str, Any]]:
    """Global "disputed zones": CONTRADICTS pairs, enriched with the conflicting
    measured values and their sources where both sides measure the same Property.

    case-specification.md names this exact scenario -- "риск противоречивых
    выводов ... по оптимальной скорости циркуляции католита". Proactively
    surfacing where the corpus disagrees (with the two numbers side by side) is
    something you can only do on a typed graph, not over retrieved text.
    """
    query = """
    MATCH (a)-[:CONTRADICTS]->(b)
    OPTIONAL MATCH (a)-[:HAS_MEASUREMENT]->(ma:Measurement)-[:MEASURES_PROPERTY]->(p:Property)
    OPTIONAL MATCH (b)-[:HAS_MEASUREMENT]->(mb:Measurement)-[:MEASURES_PROPERTY]->(p)
    RETURN a.id AS node_a, labels(a)[0] AS type_a, a.source_document AS source_a,
           b.id AS node_b, labels(b)[0] AS type_b, b.source_document AS source_b,
           p.id AS disputed_property,
           ma.value AS value_a, mb.value AS value_b, coalesce(ma.unit, mb.unit) AS unit
    LIMIT $limit
    """
    async with driver.session() as session:
        result = await session.run(query, limit=limit)
        return await result.data()


async def dashboard_summary(driver: AsyncDriver) -> dict[str, Any]:
    """Everything the management dashboard needs in one call."""
    return {
        "coverage_by_domain": await coverage_by_domain(driver),
        "gaps": await gap_detection(driver),
        "geography_only_topics": await geography_only_topics(driver),
        "risk_low_sources": await risk_zones_low_sources(driver),
        "risk_contradictions": await risk_zones_contradictions(driver),
        "contradiction_radar": await contradiction_radar(driver),
        "knowledge_evolution": await knowledge_evolution(driver),
    }
