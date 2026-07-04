"""Neo4j write repository for graph CRUD.

Node identity is `n.id` (the string the frontend uses in cy nodes / edges).
When a node is created via the API, we assign a UUID-based id if the caller
didn't supply one via `properties.id`, so downstream code can address it.

The relationship type in Neo4j is part of the schema (not a property), so we
build the type into the Cypher string. It's validated against a strict regex
first to prevent injection — Cypher parameters can't parameterize labels /
rel types.
"""

from __future__ import annotations

import logging
import re
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from neo4j import AsyncDriver

from app.features.graph.schemas import (
    FactRevisionResponse,
    GraphEdgeCreate,
    GraphEdgeResponse,
    GraphEdgeUpdate,
    GraphNodeCreate,
    GraphNodeResponse,
    GraphNodeUpdate,
)

logger = logging.getLogger(__name__)

_IDENT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")


def _validate_identifier(value: str, kind: str) -> str:
    if not _IDENT_RE.match(value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {kind}: {value!r} (letters/digits/underscore, must start with a letter)",
        )
    return value


def _node_to_response(node: Any) -> GraphNodeResponse:
    props = dict(node)
    labels = list(node.labels)
    display_id = props.get("id") or props.get("name") or node.element_id
    label = (
        props.get("name")
        or props.get("title")
        or props.get("description")
        or props.get("id")
        or (labels[0] if labels else "Node")
    )
    return GraphNodeResponse(
        id=str(display_id),
        label=str(label),
        type=labels[0] if labels else "Node",
    )


class Neo4jGraphRepository:
    def __init__(self, driver: AsyncDriver) -> None:
        self._driver = driver

    async def create_node(self, payload: GraphNodeCreate) -> GraphNodeResponse:
        label = _validate_identifier(payload.type, "node type")
        node_id = str(payload.properties.get("id") or f"n_{uuid4().hex[:12]}")
        props = {
            **payload.properties,
            "id": node_id,
            "name": payload.label,
        }
        query = f"CREATE (n:{label} $props) RETURN n"
        async with self._driver.session() as session:
            result = await session.run(query, props=props)
            record = await result.single()
        if record is None:
            raise HTTPException(status_code=500, detail="Failed to create node")
        return _node_to_response(record["n"])

    async def update_node(self, node_id: str, payload: GraphNodeUpdate) -> GraphNodeResponse:
        # Merge partial patch: label maps to `name`, `properties` merges arbitrary keys.
        updates: dict[str, Any] = {}
        if payload.label is not None:
            updates["name"] = payload.label
        if payload.properties:
            updates.update(payload.properties)
            # Never let the client overwrite the id — that would orphan edges.
            updates.pop("id", None)
        if not updates:
            existing = await self._fetch_node(node_id)
            if existing is None:
                raise HTTPException(status_code=404, detail="Node not found")
            return existing

        query = (
            "MATCH (n) WHERE n.id = $node_id OR n.name = $node_id\n"
            "SET n += $updates\n"
            "RETURN n LIMIT 1"
        )
        async with self._driver.session() as session:
            result = await session.run(query, node_id=node_id, updates=updates)
            record = await result.single()
        if record is None:
            raise HTTPException(status_code=404, detail="Node not found")
        return _node_to_response(record["n"])

    async def delete_node(self, node_id: str) -> None:
        query = (
            "MATCH (n) WHERE n.id = $node_id OR n.name = $node_id\n"
            "WITH n LIMIT 1\n"
            "DETACH DELETE n\n"
            "RETURN count(n) AS deleted"
        )
        async with self._driver.session() as session:
            result = await session.run(query, node_id=node_id)
            record = await result.single()
        if not record or (record["deleted"] or 0) == 0:
            raise HTTPException(status_code=404, detail="Node not found")

    async def create_edge(self, payload: GraphEdgeCreate) -> GraphEdgeResponse:
        rel_type = _validate_identifier(payload.type, "edge type")
        edge_id = f"e_{uuid4().hex[:12]}"
        query = (
            "MATCH (a) WHERE a.id = $source OR a.name = $source\n"
            "MATCH (b) WHERE b.id = $target OR b.name = $target\n"
            "WITH a, b LIMIT 1\n"
            f"CREATE (a)-[r:{rel_type} {{id: $edge_id, label: $label}}]->(b)\n"
            "RETURN a, r, b"
        )
        async with self._driver.session() as session:
            result = await session.run(
                query,
                source=payload.source,
                target=payload.target,
                edge_id=edge_id,
                label=payload.label,
            )
            record = await result.single()
        if record is None:
            raise HTTPException(
                status_code=404,
                detail="Source or target node not found",
            )
        return _edge_to_response(record["a"], record["r"], record["b"])

    async def update_edge(self, edge_id: str, payload: GraphEdgeUpdate) -> GraphEdgeResponse:
        query = (
            "MATCH (a)-[r]->(b) WHERE r.id = $edge_id\n"
            "SET r.label = $label\n"
            "RETURN a, r, b LIMIT 1"
        )
        async with self._driver.session() as session:
            result = await session.run(query, edge_id=edge_id, label=payload.label)
            record = await result.single()
        if record is None:
            raise HTTPException(status_code=404, detail="Edge not found")
        return _edge_to_response(record["a"], record["r"], record["b"])

    async def delete_edge(self, edge_id: str) -> None:
        query = (
            "MATCH ()-[r]->() WHERE r.id = $edge_id\n"
            "WITH r LIMIT 1\n"
            "DELETE r\n"
            "RETURN count(r) AS deleted"
        )
        async with self._driver.session() as session:
            result = await session.run(query, edge_id=edge_id)
            record = await result.single()
        if not record or (record["deleted"] or 0) == 0:
            raise HTTPException(status_code=404, detail="Edge not found")

    async def list_fact_revisions(self, fact_id: str) -> list[FactRevisionResponse]:
        query = (
            "MATCH (n) WHERE n.id = $fact_id OR n.name = $fact_id\n"
            "WITH n LIMIT 1\n"
            "MATCH (rev:Revision)-[:REVISION_OF]->(n)\n"
            "RETURN rev\n"
            "ORDER BY rev.superseded_at DESC"
        )
        async with self._driver.session() as session:
            result = await session.run(query, fact_id=fact_id)
            records = await result.data()

        return [_revision_to_response(record["rev"]) for record in records]

    async def _fetch_node(self, node_id: str) -> GraphNodeResponse | None:
        query = "MATCH (n) WHERE n.id = $node_id OR n.name = $node_id RETURN n LIMIT 1"
        async with self._driver.session() as session:
            result = await session.run(query, node_id=node_id)
            record = await result.single()
        return _node_to_response(record["n"]) if record else None


def _edge_to_response(a: Any, rel: Any, b: Any) -> GraphEdgeResponse:
    a_props = dict(a)
    b_props = dict(b)
    r_props = dict(rel)
    return GraphEdgeResponse(
        id=str(r_props.get("id") or rel.element_id),
        source=str(a_props.get("id") or a_props.get("name") or a.element_id),
        target=str(b_props.get("id") or b_props.get("name") or b.element_id),
        type=rel.type,
        label=r_props.get("label"),
    )


def _revision_to_response(revision: Any) -> FactRevisionResponse:
    props = dict(revision)
    superseded_at = str(props.pop("superseded_at", ""))
    superseded_by_document = props.pop("superseded_by_document", None)
    return FactRevisionResponse(
        superseded_at=superseded_at,
        superseded_by_document=(
            str(superseded_by_document) if superseded_by_document is not None else None
        ),
        previous_properties=props,
    )
