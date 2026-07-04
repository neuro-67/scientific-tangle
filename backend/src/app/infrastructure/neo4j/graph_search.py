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
        """Generate a Cypher query and parameter dict from the QuerySpec.

        Strategy:
        1. Start from the most specific nodes (materials, processes, equipment).
        2. Follow relationship hints if present.
        3. Apply numeric constraints on properties.
        4. Collect connected publications, findings, and measurements.
        """
        params: dict[str, Any] = {"limit": limit}

        # Build the main query with connected pattern
        query_parts: list[str] = []

        # --- Entry point and path to findings ---
        path_clause = self._build_path_clause(spec, params)
        query_parts.append(path_clause)

        # --- Node filters ---
        filter_clauses = self._build_filter_clauses(spec, params)
        if filter_clauses:
            query_parts.append("WHERE " + " AND ".join(filter_clauses))

        # --- Numeric constraints on measurements ---
        numeric_clause = self._build_numeric_clause(spec, params)
        if numeric_clause:
            query_parts.append(numeric_clause)

        # --- Time range on publications ---
        time_clause = self._build_time_clause(spec, params)
        if time_clause:
            query_parts.append(time_clause)

        # --- Geography filter ---
        geo_clause = self._build_geo_clause(spec, params)
        if geo_clause:
            query_parts.append(geo_clause)

        # --- RETURN with scoring ---
        query_parts.append(self._build_return_clause(spec))

        query = "\n".join(query_parts)
        return query, params

    def _build_path_clause(self, spec: QuerySpec, params: dict[str, Any]) -> str:
        """Build the main MATCH pattern connecting entities to findings."""
        if spec.materials:
            params["materials"] = spec.materials
            return """
            MATCH (m:Material)
            WHERE m.id IN $materials
            OPTIONAL MATCH (m)-[:USES_MATERIAL|APPLIES_TO|OPERATES_AT_CONDITION|HAS_MEASUREMENT|USES_EQUIPMENT|SHOWED|DESCRIBED_IN*1..3]-(f:Finding)
            OPTIONAL MATCH (f)-[:DESCRIBED_IN]->(pub:Publication)
            OPTIONAL MATCH (f)-[:HAS_SOURCE]->(src:Source)
            """
        elif spec.processes:
            params["processes"] = spec.processes
            return """
            MATCH (p:Process)
            WHERE p.id IN $processes
            OPTIONAL MATCH (p)-[:USES_MATERIAL|APPLIES_TO|OPERATES_AT_CONDITION|HAS_MEASUREMENT|USES_EQUIPMENT|SHOWED|DESCRIBED_IN*1..3]-(f:Finding)
            OPTIONAL MATCH (f)-[:DESCRIBED_IN]->(pub:Publication)
            OPTIONAL MATCH (f)-[:HAS_SOURCE]->(src:Source)
            """
        elif spec.equipment:
            params["equipment"] = spec.equipment
            return """
            MATCH (e:Equipment)
            WHERE e.id IN $equipment
            OPTIONAL MATCH (e)-[:USES_MATERIAL|APPLIES_TO|OPERATES_AT_CONDITION|HAS_MEASUREMENT|USES_EQUIPMENT|SHOWED|DESCRIBED_IN*1..3]-(f:Finding)
            OPTIONAL MATCH (f)-[:DESCRIBED_IN]->(pub:Publication)
            OPTIONAL MATCH (f)-[:HAS_SOURCE]->(src:Source)
            """
        elif spec.properties:
            params["properties"] = spec.properties
            return """
            MATCH (prop:Property)
            WHERE prop.id IN $properties
            OPTIONAL MATCH (prop)-[:USES_MATERIAL|APPLIES_TO|OPERATES_AT_CONDITION|HAS_MEASUREMENT|USES_EQUIPMENT|SHOWED|DESCRIBED_IN*1..3]-(f:Finding)
            OPTIONAL MATCH (f)-[:DESCRIBED_IN]->(pub:Publication)
            OPTIONAL MATCH (f)-[:HAS_SOURCE]->(src:Source)
            """
        elif spec.conditions:
            params["conditions"] = spec.conditions
            return """
            MATCH (c:Condition)
            WHERE c.id IN $conditions
            OPTIONAL MATCH (c)-[:USES_MATERIAL|APPLIES_TO|OPERATES_AT_CONDITION|HAS_MEASUREMENT|USES_EQUIPMENT|SHOWED|DESCRIBED_IN*1..3]-(f:Finding)
            OPTIONAL MATCH (f)-[:DESCRIBED_IN]->(pub:Publication)
            OPTIONAL MATCH (f)-[:HAS_SOURCE]->(src:Source)
            """
        elif spec.experts:
            params["experts"] = spec.experts
            return """
            MATCH (ex:Expert)
            WHERE ex.id IN $experts
            OPTIONAL MATCH (ex)-[:USES_MATERIAL|APPLIES_TO|OPERATES_AT_CONDITION|HAS_MEASUREMENT|USES_EQUIPMENT|SHOWED|DESCRIBED_IN*1..3]-(f:Finding)
            OPTIONAL MATCH (f)-[:DESCRIBED_IN]->(pub:Publication)
            OPTIONAL MATCH (f)-[:HAS_SOURCE]->(src:Source)
            """
        elif spec.facilities:
            params["facilities"] = spec.facilities
            return """
            MATCH (fac:Facility)
            WHERE fac.id IN $facilities
            OPTIONAL MATCH (fac)-[:USES_MATERIAL|APPLIES_TO|OPERATES_AT_CONDITION|HAS_MEASUREMENT|USES_EQUIPMENT|SHOWED|DESCRIBED_IN*1..3]-(f:Finding)
            OPTIONAL MATCH (f)-[:DESCRIBED_IN]->(pub:Publication)
            OPTIONAL MATCH (f)-[:HAS_SOURCE]->(src:Source)
            """
        else:
            return """
            MATCH (f:Finding)
            OPTIONAL MATCH (f)-[:DESCRIBED_IN]->(pub:Publication)
            OPTIONAL MATCH (f)-[:HAS_SOURCE]->(src:Source)
            """

    def _build_filter_clauses(self, spec: QuerySpec, params: dict[str, Any]) -> list[str]:
        """Build additional WHERE clauses for secondary entity filters."""
        clauses: list[str] = []
        # For now, secondary filtering is done through path traversal
        return clauses

    def _build_numeric_clause(self, spec: QuerySpec, params: dict[str, Any]) -> str:
        """Build numeric constraint clause with proper parameter binding."""
        if not spec.numeric_constraints:
            return ""
        conditions: list[str] = []
        for i, nc in enumerate(spec.numeric_constraints):
            if nc.operator == "range" and nc.min is not None and nc.max is not None:
                params[f"prop_{i}"] = nc.property
                params[f"min_{i}"] = nc.min
                params[f"max_{i}"] = nc.max
                conditions.append(
                    f"(meas.id = $prop_{i} AND meas.value >= $min_{i} AND meas.value <= $max_{i})"
                )
            elif nc.value is not None:
                params[f"prop_{i}"] = nc.property
                params[f"val_{i}"] = nc.value
                op = nc.operator if nc.operator in ("<=", ">=", "=") else "<="
                conditions.append(
                    f"(meas.id = $prop_{i} AND meas.value {op} $val_{i})"
                )
        if not conditions:
            return ""
        return f"""
        MATCH (f)-[:HAS_MEASUREMENT]->(meas:Measurement)
        WHERE {" OR ".join(conditions)}
        """

    def _build_time_clause(self, spec: QuerySpec, params: dict[str, Any]) -> str:
        """Build publication year filter."""
        if spec.time_range.from_year is None and spec.time_range.to_year is None:
            return ""
        conditions: list[str] = []
        if spec.time_range.from_year is not None:
            params["from_year"] = spec.time_range.from_year
            conditions.append("pub.year >= $from_year")
        if spec.time_range.to_year is not None:
            params["to_year"] = spec.time_range.to_year
            conditions.append("pub.year <= $to_year")
        return f"""
        WITH f, pub, src
        WHERE {' AND '.join(conditions)}
        """

    def _build_geo_clause(self, spec: QuerySpec, params: dict[str, Any]) -> str:
        """Build geography filter."""
        if spec.geography.value == "any":
            return ""
        params["geography"] = spec.geography.value
        return """
        WITH f, pub, src
        WHERE pub.geography = $geography
        """

    def _build_return_clause(self, spec: QuerySpec) -> str:
        """Build RETURN clause with all relevant fields.

        f.confidence is stored as either a string ("high"/"medium"/"low", set
        by the LLM extractor on Finding nodes) or a float default (0.5, set by
        neo4j_import.py for nodes without an explicit confidence) -- ORDER BY
        on the raw mixed-type property would not rank meaningfully, so rank
        via an explicit CASE instead.
        """
        return """
        RETURN f.id as finding_text,
               f.confidence as finding_confidence,
               f.description as finding_description,
               pub.id as source_title,
               pub.year as source_year,
               pub.geography as source_geography,
               src.span as span,
               f.ingestion_date as extracted_at
        ORDER BY CASE toString(f.confidence)
                   WHEN 'high' THEN 3 WHEN 'medium' THEN 2 WHEN 'low' THEN 1 ELSE 0
                 END DESC
        LIMIT $limit
        """
