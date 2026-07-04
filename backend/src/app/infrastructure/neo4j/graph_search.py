"""Neo4j adapter implementing the graph-search port.

Builds parameterized Cypher from a QuerySpec and executes it against Neo4j.
"""

from __future__ import annotations

import logging
from typing import Any

from neo4j import AsyncDriver

from app.domain.interfaces.graph_search import IGraphSearch
from nlp.query.schemas import QuerySpec

logger = logging.getLogger(__name__)

_FINDING_HOP = (
    "OPTIONAL MATCH (entry)"
    "-[:USES_MATERIAL|APPLIES_TO|OPERATES_AT_CONDITION|HAS_MEASUREMENT|"
    "USES_EQUIPMENT|SHOWED|DESCRIBED_IN|AUTHORED_BY|VALIDATED_BY|"
    "CONDUCTED_AT|EXPERT_IN|HAS_SOURCE*1..3]-(f:Finding)\n"
    "OPTIONAL MATCH (f)-[:DESCRIBED_IN]->(pub:Publication)\n"
    "OPTIONAL MATCH (f)-[:HAS_SOURCE]->(src:Source)"
)


class Neo4jGraphSearch(IGraphSearch):
    """Executes Cypher queries built from QuerySpec against Neo4j."""

    def __init__(self, driver: AsyncDriver) -> None:
        self._driver = driver

    async def search(self, spec: QuerySpec, limit: int = 20) -> list[dict[str, Any]]:
        query, params = self._build_cypher(spec, limit)
        logger.debug("cypher query", extra={"query": query, "params": params})
        async with self._driver.session() as session:
            result = await session.run(query, **params)
            records = await result.data()
            return records

    async def get_entity_context(self, entity_name: str, entity_type: str) -> dict[str, Any] | None:
        query = """
        MATCH (n {name: $name})
        WHERE $type IN labels(n)
        OPTIONAL MATCH (n)-[r]-(m)
        RETURN n, collect({rel: type(r), node: m}) as neighbours
        LIMIT 1
        """
        async with self._driver.session() as session:
            result = await session.run(query, name=entity_name, type=entity_type)
            record = await result.single()
            return dict(record) if record else None

    # ------------------------------------------------------------------
    # Cypher builder
    # ------------------------------------------------------------------

    def _build_cypher(self, spec: QuerySpec, limit: int) -> tuple[str, dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit}

        query_parts: list[str] = []
        query_parts.append(self._build_path_clause(spec, params))

        numeric_clause = self._build_numeric_clause(spec, params)
        if numeric_clause:
            query_parts.append(numeric_clause)

        time_clause = self._build_time_clause(spec, params)
        if time_clause:
            query_parts.append(time_clause)

        geo_clause = self._build_geo_clause(spec, params)
        if geo_clause:
            query_parts.append(geo_clause)

        query_parts.append(self._build_return_clause())

        return "\n".join(query_parts), params

    def _build_path_clause(self, spec: QuerySpec, params: dict[str, Any]) -> str:
        """Build the MATCH pattern.

        Each branch unifies the entry node under a common `entry` variable so
        the downstream WITH/RETURN can quote a single set of columns regardless
        of which entity type kicked off the retrieval. The fallback (no filters
        in the spec) matches any meta-node so questions about authors, orgs,
        or standalone measurements still surface results even when no Finding
        exists in the graph yet.
        """
        primary_branches: list[tuple[str, list[str] | None, str]] = [
            ("Material", spec.materials, "materials"),
            ("Process", spec.processes, "processes"),
            ("Equipment", spec.equipment, "equipment"),
            ("Property", spec.properties, "properties"),
            ("Condition", spec.conditions, "conditions"),
            ("Expert", spec.experts, "experts"),
            ("Facility", spec.facilities, "facilities"),
        ]
        for label, values, key in primary_branches:
            if not values:
                continue
            params[key] = values
            return (
                f"MATCH (entry:{label})\n"
                f"WHERE entry.id IN ${key} OR entry.name IN ${key}\n"
                f"{_FINDING_HOP}"
            )

        # Fallback: no primary entity was pulled out of the question. Search
        # broadly across meta-nodes so we can still answer meta questions
        # ("кто автор?", "какие организации?") on a graph that has no Finding
        # nodes yet.
        return (
            "MATCH (entry)\n"
            "WHERE any(l IN labels(entry) WHERE l IN "
            "['Finding','Publication','Expert','Facility','Measurement','Material','Process'])\n"
            "OPTIONAL MATCH (entry)-[:DESCRIBED_IN]->(pub:Publication)\n"
            "OPTIONAL MATCH (entry)-[:HAS_SOURCE]->(src:Source)\n"
            "WITH entry, pub, src, "
            "CASE WHEN 'Finding' IN labels(entry) THEN entry ELSE null END AS f"
        )

    def _build_numeric_clause(self, spec: QuerySpec, params: dict[str, Any]) -> str:
        if not spec.numeric_constraints:
            return ""
        conditions: list[str] = []
        for i, nc in enumerate(spec.numeric_constraints):
            params[f"prop_{i}"] = nc.property
            if nc.operator == "range" and nc.min is not None and nc.max is not None:
                params[f"min_{i}"] = nc.min
                params[f"max_{i}"] = nc.max
                conditions.append(
                    f"(prop.id = $prop_{i} AND "
                    f"((meas.operator = 'range' AND meas.min <= $max_{i} AND meas.max >= $min_{i}) "
                    f"OR (meas.value IS NOT NULL AND meas.value >= $min_{i} AND meas.value <= $max_{i})))"
                )
            elif nc.value is not None:
                params[f"val_{i}"] = nc.value
                op = nc.operator if nc.operator in ("<=", ">=", "=") else "<="
                conditions.append(
                    f"(prop.id = $prop_{i} AND "
                    f"((meas.value IS NOT NULL AND meas.value {op} $val_{i}) "
                    f"OR (meas.max IS NOT NULL AND meas.max {op} $val_{i}) "
                    f"OR (meas.min IS NOT NULL AND meas.min {op} $val_{i})))"
                )
        if not conditions:
            return ""
        return (
            "WITH entry, f, pub, src\n"
            "MATCH (f)-[:HAS_MEASUREMENT]->(meas:Measurement)-[:MEASURES_PROPERTY]->(prop:Property)\n"
            f"WHERE {' OR '.join(conditions)}\n"
            "WITH entry, f, pub, src, meas, prop"
        )

    def _build_time_clause(self, spec: QuerySpec, params: dict[str, Any]) -> str:
        if spec.time_range.from_year is None and spec.time_range.to_year is None:
            return ""
        conditions: list[str] = []
        if spec.time_range.from_year is not None:
            params["from_year"] = spec.time_range.from_year
            conditions.append("pub.year >= $from_year")
        if spec.time_range.to_year is not None:
            params["to_year"] = spec.time_range.to_year
            conditions.append("pub.year <= $to_year")
        return (
            "WITH entry, f, pub, src\n"
            f"WHERE {' AND '.join(conditions)}"
        )

    def _build_geo_clause(self, spec: QuerySpec, params: dict[str, Any]) -> str:
        if spec.geography.value == "any":
            return ""
        params["geography"] = spec.geography.value
        return (
            "WITH entry, f, pub, src\n"
            "WHERE COALESCE(pub.geography, entry.geography) = $geography"
        )

    def _build_return_clause(self) -> str:
        """RETURN unified across all path branches.

        finding_text falls back through: Finding.description → Finding.id →
        an assembled meta-string ("Expert: name — position", "Publication:
        title", "Measurement: 500 сотрудников") so the synthesizer still
        receives usable context even when no Finding node exists.
        """
        return """
        RETURN
            COALESCE(
                f.description,
                f.id,
                CASE WHEN entry IS NULL THEN NULL
                     WHEN 'Expert' IN labels(entry)
                       THEN 'Эксперт: ' + COALESCE(entry.name, entry.id)
                         + CASE WHEN entry.position IS NOT NULL
                                THEN ' — ' + entry.position ELSE '' END
                         + CASE WHEN entry.email IS NOT NULL
                                THEN ' (' + entry.email + ')' ELSE '' END
                     WHEN 'Publication' IN labels(entry)
                       THEN 'Публикация: ' + COALESCE(entry.name, entry.id)
                     WHEN 'Facility' IN labels(entry)
                       THEN 'Организация: ' + COALESCE(entry.name, entry.id)
                     WHEN 'Measurement' IN labels(entry)
                       THEN 'Измерение: ' + toString(COALESCE(entry.value, entry.min))
                         + CASE WHEN entry.unit IS NOT NULL
                                THEN ' ' + entry.unit ELSE '' END
                     WHEN 'Material' IN labels(entry)
                       THEN 'Материал: ' + COALESCE(entry.name, entry.id)
                     WHEN 'Process' IN labels(entry)
                       THEN 'Процесс: ' + COALESCE(entry.name, entry.id)
                     ELSE COALESCE(entry.name, entry.id) END
            ) AS finding_text,
            COALESCE(f.confidence, entry.confidence) AS finding_confidence,
            COALESCE(f.description, entry.description) AS finding_description,
            COALESCE(pub.id, pub.name, entry.source_document) AS source_title,
            pub.year AS source_year,
            COALESCE(pub.geography, entry.geography) AS source_geography,
            src.span AS span,
            COALESCE(f.ingestion_date, entry.ingestion_date) AS extracted_at
        ORDER BY CASE toString(COALESCE(f.confidence, entry.confidence))
                    WHEN 'high' THEN 3 WHEN 'medium' THEN 2 WHEN 'low' THEN 1
                    ELSE 0
                 END DESC
        LIMIT $limit
        """
