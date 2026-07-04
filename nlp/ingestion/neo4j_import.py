"""Import knowledge graphs from ML-1 JSON into Neo4j.

Usage:
    python -m nlp.ingestion.neo4j_import nlp/pdftest_graph.json
    python -m nlp.ingestion.neo4j_import nlp/test_graph.json

Requires NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD env vars.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any

from neo4j import GraphDatabase

logger = logging.getLogger(__name__)

# Mapping from ML-1 node labels to Neo4j labels
_LABEL_MAP = {
    "Material": "Material",
    "Process": "Process",
    "Equipment": "Equipment",
    "Property": "Property",
    "Measurement": "Measurement",
    "Condition": "Condition",
    "Experiment": "Experiment",
    "Publication": "Publication",
    "Expert": "Expert",
    "Facility": "Facility",
    "Finding": "Finding",
    "Topic": "Topic",
    "Source": "Source",  # provenance node (docs/ONTOLOGY.md)
    "Model": "Model",  # ML-1 extension
}

# Mapping from ML-1 edge types to Neo4j relationship types
_REL_MAP = {
    "uses_material": "USES_MATERIAL",
    "applies_to": "APPLIES_TO",
    "operates_at_condition": "OPERATES_AT_CONDITION",
    "has_measurement": "HAS_MEASUREMENT",
    "measures_property": "MEASURES_PROPERTY",
    "uses_equipment": "USES_EQUIPMENT",
    "uses_process": "USES_PROCESS",
    "produces_output": "PRODUCES_OUTPUT",
    "showed": "SHOWED",
    "described_in": "DESCRIBED_IN",
    "authored_by": "AUTHORED_BY",
    "expert_in": "EXPERT_IN",
    "conducted_at": "CONDUCTED_AT",
    "validated_by": "VALIDATED_BY",
    "contradicts": "CONTRADICTS",
    "supports": "SUPPORTS",
    "tagged": "TAGGED",
    "has_source": "HAS_SOURCE",
}


def _get_neo4j_driver():
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "neo4j_password")
    return GraphDatabase.driver(uri, auth=(user, password))


def _sanitize_id(node_id: str) -> str:
    """Sanitize node ID for use as a Neo4j identifier."""
    # Replace problematic characters but keep Cyrillic
    sanitized = node_id.strip().replace("'", "\\'")
    return sanitized


def _validate_node(node: dict[str, Any], source_doc: str) -> dict[str, Any] | None:
    """Validate and enrich a node with metadata.

    Returns None if the node is invalid and should be skipped.
    """
    node_id = node.get("id", "").strip()
    label = node.get("label", "").strip()

    if not node_id:
        logger.warning("skipping node with empty id", extra={"source": source_doc})
        return None

    if not label:
        logger.warning("skipping node with empty label", extra={"id": node_id, "source": source_doc})
        return None

    # Map to canonical label
    canonical_label = _LABEL_MAP.get(label)
    if not canonical_label:
        logger.warning(
            "unknown node label, using as-is",
            extra={"label": label, "id": node_id, "source": source_doc},
        )
        canonical_label = label

    # Build enriched node
    enriched = {
        "id": _sanitize_id(node_id),
        "label": canonical_label,
        "properties": node.get("properties", {}),
        "source_document": source_doc,
        "ingestion_date": datetime.utcnow().isoformat(),
        "validation_status": "pending",  # pending | validated | rejected
        "confidence": node.get("properties", {}).get("confidence", 0.5),
    }

    return enriched


def _validate_edge(edge: dict[str, Any], source_doc: str) -> dict[str, Any] | None:
    """Validate and enrich an edge with metadata."""
    source = edge.get("source", "").strip()
    target = edge.get("target", "").strip()
    edge_type = edge.get("type", "").strip()

    if not source or not target or not edge_type:
        logger.warning("skipping edge with missing fields", extra={"source": source_doc})
        return None

    # Map to canonical relationship type
    canonical_type = _REL_MAP.get(edge_type)
    if not canonical_type:
        logger.warning(
            "unknown edge type, using as-is",
            extra={"type": edge_type, "source": source_doc},
        )
        canonical_type = edge_type.upper().replace(" ", "_")

    enriched = {
        "source": _sanitize_id(source),
        "target": _sanitize_id(target),
        "type": canonical_type,
        "source_document": source_doc,
        "ingestion_date": datetime.utcnow().isoformat(),
        "validation_status": "pending",
    }

    return enriched


def _create_constraints(tx):
    """Create uniqueness constraints on node IDs."""
    for label in _LABEL_MAP.values():
        try:
            tx.run(f"""
                CREATE CONSTRAINT {label.lower()}_id_unique IF NOT EXISTS
                FOR (n:{label}) REQUIRE n.id IS UNIQUE
            """)
        except Exception as exc:
            logger.warning(f"constraint creation failed for {label}", extra={"error": str(exc)})


# Properties that make a Measurement/Finding a "fact" whose change is worth
# keeping history for (case-specification.md: "Версионирование фактов:
# отслеживание изменений в выводах, обновление данных при появлении новых
# источников"). Administrative fields (ingestion_date, source_document,
# validation_status) always change on re-import and would version every
# single re-run for no reason, so they're excluded.
_FACT_FIELDS: dict[str, tuple[str, ...]] = {
    "Measurement": ("value", "min", "max", "unit", "operator"),
    "Finding": ("confidence",),
}


def _fact_changed(old_props: dict[str, Any], new_props: dict[str, Any], label: str) -> bool:
    fields = _FACT_FIELDS.get(label, ())
    return any(old_props.get(f) != new_props.get(f) for f in fields)


def _archive_previous_version(tx, node_id: str, label: str, old_props: dict[str, Any], superseded_by: str) -> None:
    """Snapshot a Measurement/Finding's prior properties onto a :Revision
    node before overwriting it, instead of losing the old value to MERGE's
    last-write-wins SET."""
    tx.run(
        """
        MATCH (n {id: $id})
        CREATE (rev:Revision)
        SET rev = $old_props, rev.superseded_at = $superseded_at, rev.superseded_by_document = $superseded_by
        CREATE (rev)-[:REVISION_OF]->(n)
        """,
        id=node_id,
        old_props=old_props,
        superseded_at=datetime.utcnow().isoformat(),
        superseded_by=superseded_by,
    )


def _import_nodes(tx, nodes: list[dict[str, Any]]):
    """Import nodes into Neo4j."""
    for node in nodes:
        props = node.get("properties", {})
        # Flatten properties for Neo4j storage
        flat_props = {
            "id": node["id"],
            "source_document": node["source_document"],
            "ingestion_date": node["ingestion_date"],
            "validation_status": node["validation_status"],
            "confidence": node["confidence"],
        }
        # Add original properties
        for k, v in props.items():
            if k not in flat_props:
                flat_props[k] = v

        label = node["label"]

        if label in _FACT_FIELDS:
            existing = tx.run(f"MATCH (n:{label} {{id: $id}}) RETURN n AS n", id=node["id"]).single()
            if existing is not None:
                old_props = dict(existing["n"])
                if _fact_changed(old_props, flat_props, label):
                    _archive_previous_version(tx, node["id"], label, old_props, flat_props["source_document"])
                    logger.info(
                        "archived previous fact version",
                        extra={"id": node["id"], "label": label, "superseded_by": flat_props["source_document"]},
                    )

        query = f"""
        MERGE (n:{label} {{id: $id}})
        SET n += $props
        """
        tx.run(query, id=node["id"], props=flat_props)


def _import_edges(tx, edges: list[dict[str, Any]]):
    """Import edges into Neo4j."""
    for edge in edges:
        query = f"""
        MATCH (a {{id: $source}})
        MATCH (b {{id: $target}})
        MERGE (a)-[r:{edge['type']}]->(b)
        SET r.source_document = $source_document,
            r.ingestion_date = $ingestion_date,
            r.validation_status = $validation_status
        """
        tx.run(
            query,
            source=edge["source"],
            target=edge["target"],
            source_document=edge["source_document"],
            ingestion_date=edge["ingestion_date"],
            validation_status=edge["validation_status"],
        )


def import_graph(graph_path: str, driver) -> dict[str, int]:
    """Import a single graph JSON file into Neo4j.

    Returns stats: {nodes_total, nodes_valid, edges_total, edges_valid}
    """
    logger.info("loading graph", extra={"path": graph_path})
    with open(graph_path, encoding="utf-8") as f:
        data = json.load(f)

    source_doc = data.get("document", graph_path)
    raw_nodes = data.get("nodes", [])
    raw_edges = data.get("edges", [])

    # Validate and enrich
    valid_nodes = []
    for n in raw_nodes:
        enriched = _validate_node(n, source_doc)
        if enriched:
            valid_nodes.append(enriched)

    valid_edges = []
    for e in raw_edges:
        enriched = _validate_edge(e, source_doc)
        if enriched:
            valid_edges.append(enriched)

    logger.info(
        "validation complete",
        extra={
            "nodes_total": len(raw_nodes),
            "nodes_valid": len(valid_nodes),
            "edges_total": len(raw_edges),
            "edges_valid": len(valid_edges),
        },
    )

    # Import into Neo4j
    with driver.session() as session:
        # Create constraints
        session.execute_write(_create_constraints)

        # Import nodes
        session.execute_write(_import_nodes, valid_nodes)
        logger.info("nodes imported", extra={"count": len(valid_nodes)})

        # Import edges
        session.execute_write(_import_edges, valid_edges)
        logger.info("edges imported", extra={"count": len(valid_edges)})

    return {
        "nodes_total": len(raw_nodes),
        "nodes_valid": len(valid_nodes),
        "edges_total": len(raw_edges),
        "edges_valid": len(valid_edges),
    }


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python -m nlp.ingestion.neo4j_import <graph.json> [graph2.json ...]")
        sys.exit(1)

    driver = _get_neo4j_driver()

    try:
        for path in sys.argv[1:]:
            stats = import_graph(path, driver)
            print(f"\nImported {path}:")
            print(f"  Nodes: {stats['nodes_valid']}/{stats['nodes_total']}")
            print(f"  Edges: {stats['edges_valid']}/{stats['edges_total']}")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
