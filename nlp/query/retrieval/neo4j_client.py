"""Neo4j connection and Cypher query builder for graph retrieval."""

from __future__ import annotations

from typing import Any

from neo4j import AsyncGraphDatabase

from nlp.query.schemas import QuerySpec


class Neo4jClient:
    """Async Neo4j client with Cypher query builder."""

    def __init__(self, uri: str, user: str, password: str) -> None:
        self._driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    async def close(self) -> None:
        await self._driver.close()

    async def health(self) -> bool:
        try:
            async with self._driver.session() as session:
                await session.run("RETURN 1")
            return True
        except Exception:
            return False

    async def search_graph(self, spec: QuerySpec, limit: int = 20) -> list[dict]:
        """Execute Cypher query built from QuerySpec."""
        query, params = self._build_cypher(spec, limit)
        async with self._driver.session() as session:
            result = await session.run(query, params)
            records = await result.data()
            return records

    def _build_cypher(self, spec: QuerySpec, limit: int) -> tuple[str, dict[str, Any]]:
        """Build Cypher query from QuerySpec.

        Returns (query_string, parameters).
        """
        conditions: list[str] = []
        params: dict[str, Any] = {"limit": limit}

        # Material filter
        if spec.materials:
            conditions.append(
                "ANY(m IN $materials WHERE (n:Material AND n.id = m) "
                "OR EXISTS { (n)-[:USES_MATERIAL|APPLIES_TO]->(mat:Material) "
                "WHERE mat.id IN $materials } )"
            )
            params["materials"] = spec.materials

        # Process filter
        if spec.processes:
            conditions.append(
                "ANY(p IN $processes WHERE (n:Process AND n.id = p) "
                "OR EXISTS { (n)-[:USES_MATERIAL|OPERATES_AT_CONDITION|PRODUCES_OUTPUT]->() "
                "<-[:USES_MATERIAL|OPERATES_AT_CONDITION|PRODUCES_OUTPUT]-(proc:Process) "
                "WHERE proc.id IN $processes } )"
            )
            params["processes"] = spec.processes

        # Geography filter on Publication
        if spec.geography.value != "any":
            conditions.append(
                "EXISTS { (n)-[:DESCRIBED_IN]->(pub:Publication) "
                "WHERE pub.geography = $geo }"
            )
            params["geo"] = spec.geography.value

        # Time range filter on Publication
        if spec.time_range.from_year or spec.time_range.to_year:
            time_conds = []
            if spec.time_range.from_year:
                time_conds.append("pub.year >= $from_year")
                params["from_year"] = spec.time_range.from_year
            if spec.time_range.to_year:
                time_conds.append("pub.year <= $to_year")
                params["to_year"] = spec.time_range.to_year
            conditions.append(
                "EXISTS { (n)-[:DESCRIBED_IN]->(pub:Publication) WHERE "
                + " AND ".join(time_conds) + " }"
            )

        # Numeric constraints on Measurement. Property name is not an
        # attribute of Measurement itself (there is no meas.property) --
        # it lives on a separate Property node linked via
        # MEASURES_PROPERTY (docs/ONTOLOGY.md; nlp/ingestion/neo4j_import.py
        # writes it that way). Matching meas.property directly never
        # matched anything -- confirmed empirically with a synthetic test.
        for i, nc in enumerate(spec.numeric_constraints):
            prefix = f"nc{i}"
            meas_match = (
                f"EXISTS {{ (n)-[:HAS_MEASUREMENT]->(meas:Measurement)-[:MEASURES_PROPERTY]->(prop:Property) "
                f"WHERE prop.id = ${prefix}_prop"
            )
            params[f"{prefix}_prop"] = nc.property

            if nc.unit:
                meas_match += f" AND meas.unit = ${prefix}_unit"
                params[f"{prefix}_unit"] = nc.unit

            if nc.operator == "range" and nc.min is not None and nc.max is not None:
                meas_match += (
                    f" AND ((meas.operator = 'range' AND meas.min <= ${prefix}_max AND meas.max >= ${prefix}_min) "
                    f"OR (meas.value IS NOT NULL AND meas.value >= ${prefix}_min AND meas.value <= ${prefix}_max))"
                )
                params[f"{prefix}_min"] = nc.min
                params[f"{prefix}_max"] = nc.max
            elif nc.value is not None:
                if nc.operator == "<=":
                    meas_match += f" AND ((meas.value IS NOT NULL AND meas.value <= ${prefix}_val) OR (meas.max IS NOT NULL AND meas.max <= ${prefix}_val))"
                elif nc.operator == ">=":
                    meas_match += f" AND ((meas.value IS NOT NULL AND meas.value >= ${prefix}_val) OR (meas.min IS NOT NULL AND meas.min >= ${prefix}_val))"
                elif nc.operator == "=":
                    meas_match += f" AND ((meas.value IS NOT NULL AND meas.value = ${prefix}_val) OR (meas.min <= ${prefix}_val AND meas.max >= ${prefix}_val))"
                params[f"{prefix}_val"] = nc.value

            meas_match += " }"
            conditions.append(meas_match)

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        query = f"""
        MATCH (n)
        WHERE {where_clause}
        WITH n
        OPTIONAL MATCH (n)-[:DESCRIBED_IN]->(pub:Publication)
        OPTIONAL MATCH (n)-[:HAS_SOURCE]->(src:Source)
        RETURN n.id AS name,
               labels(n) AS types,
               n.confidence AS confidence,
               pub.title AS source_title,
               pub.year AS source_year,
               pub.geography AS source_geo,
               src.span AS span,
               n.source_document AS doc_id,
               n.ingestion_date AS extracted_at
        LIMIT $limit
        """
        return query, params

    async def get_subgraph(
        self,
        node_names: list[str],
        depth: int = 2,
    ) -> list[dict]:
        """Extract subgraph around given nodes for visualization."""
        query = f"""
        UNWIND $node_names AS name
        MATCH (n {{id: name}})
        CALL apoc.path.subgraphNodes(n, {{
            relationshipFilter: null,
            minLevel: 0,
            maxLevel: {depth}
        }}) YIELD node
        WITH DISTINCT node
        OPTIONAL MATCH (node)-[r]->(m)
        RETURN node.id AS source,
               type(r) AS relation,
               m.id AS target,
               labels(node) AS source_labels,
               labels(m) AS target_labels
        """
        async with self._driver.session() as session:
            result = await session.run(query, {"node_names": node_names})
            return await result.data()
