"""Answer-scoped graph mutations.

Every write goes to Neo4j via `Neo4jGraphRepository` AND patches the answer's
`subgraph` snapshot in the answers table, so re-opening the answer shows
exactly what the user built — including orphan nodes (comments, ad-hoc
additions) that the QuerySpec-based subgraph fetch would never retrieve.
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import HTTPException, status

from app.features.graph.repository import Neo4jGraphRepository
from app.features.graph.schemas import (
    GraphEdgeCreate,
    GraphEdgeResponse,
    GraphEdgeUpdate,
    GraphNodeCreate,
    GraphNodeResponse,
    GraphNodeUpdate,
)
from app.features.query.history.repository import AnswersRepository

logger = logging.getLogger(__name__)


class AnswerGraphMutations:
    def __init__(
        self,
        answers: AnswersRepository,
        graph: Neo4jGraphRepository,
    ) -> None:
        self._answers = answers
        self._graph = graph

    async def _load_subgraph(self, answer_id: UUID) -> dict[str, list[dict]]:
        record = await self._answers.get_by_id(answer_id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found"
            )
        subgraph = record.subgraph or {}
        return {
            "nodes": list(subgraph.get("nodes") or []),
            "edges": list(subgraph.get("edges") or []),
        }

    async def _save_subgraph(
        self, answer_id: UUID, subgraph: dict[str, list[dict]]
    ) -> None:
        try:
            await self._answers.patch_subgraph(answer_id, subgraph)
        except Exception as exc:
            # Non-fatal: Neo4j is already updated, snapshot drift is recoverable
            # (regenerate re-syncs). Log and move on.
            logger.warning(
                "answer snapshot patch failed",
                extra={"answer_id": str(answer_id), "error": str(exc)},
            )

    async def create_node(
        self, answer_id: UUID, payload: GraphNodeCreate
    ) -> GraphNodeResponse:
        subgraph = await self._load_subgraph(answer_id)
        created = await self._graph.create_node(payload)
        subgraph["nodes"].append(
            {"id": created.id, "label": created.label, "type": created.type}
        )
        await self._save_subgraph(answer_id, subgraph)
        return created

    async def update_node(
        self, answer_id: UUID, node_id: str, payload: GraphNodeUpdate
    ) -> GraphNodeResponse:
        subgraph = await self._load_subgraph(answer_id)
        updated = await self._graph.update_node(node_id, payload)
        for node in subgraph["nodes"]:
            if node.get("id") == node_id:
                node["label"] = updated.label
                node["type"] = updated.type
        await self._save_subgraph(answer_id, subgraph)
        return updated

    async def delete_node(self, answer_id: UUID, node_id: str) -> None:
        subgraph = await self._load_subgraph(answer_id)
        await self._graph.delete_node(node_id)
        subgraph["nodes"] = [n for n in subgraph["nodes"] if n.get("id") != node_id]
        # DETACH DELETE removed connected edges in Neo4j — mirror on snapshot.
        subgraph["edges"] = [
            e
            for e in subgraph["edges"]
            if e.get("source") != node_id and e.get("target") != node_id
        ]
        await self._save_subgraph(answer_id, subgraph)

    async def create_edge(
        self, answer_id: UUID, payload: GraphEdgeCreate
    ) -> GraphEdgeResponse:
        subgraph = await self._load_subgraph(answer_id)
        created = await self._graph.create_edge(payload)
        subgraph["edges"].append(
            {
                "id": created.id,
                "source": created.source,
                "target": created.target,
                "type": created.type,
                "label": created.label,
            }
        )
        await self._save_subgraph(answer_id, subgraph)
        return created

    async def update_edge(
        self, answer_id: UUID, edge_id: str, payload: GraphEdgeUpdate
    ) -> GraphEdgeResponse:
        subgraph = await self._load_subgraph(answer_id)
        updated = await self._graph.update_edge(edge_id, payload)
        for edge in subgraph["edges"]:
            if edge.get("id") == edge_id:
                edge["label"] = updated.label
                edge["type"] = updated.type
        await self._save_subgraph(answer_id, subgraph)
        return updated

    async def delete_edge(self, answer_id: UUID, edge_id: str) -> None:
        subgraph = await self._load_subgraph(answer_id)
        await self._graph.delete_edge(edge_id)
        subgraph["edges"] = [e for e in subgraph["edges"] if e.get("id") != edge_id]
        await self._save_subgraph(answer_id, subgraph)
