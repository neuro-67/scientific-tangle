"""HTTP routes for graph node/edge CRUD."""

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, status

from app.features.graph.repository import Neo4jGraphRepository
from app.features.graph.schemas import (
    FactRevisionResponse,
    GraphEdgeCreate,
    GraphEdgeResponse,
    GraphEdgeUpdate,
    GraphNodeCreate,
    GraphNodeResponse,
    GraphNodeUpdate,
)

router = APIRouter(tags=["graph"], prefix="/graph")


@router.post("/nodes", response_model=GraphNodeResponse, status_code=status.HTTP_201_CREATED)
@inject
async def create_node(
    payload: GraphNodeCreate,
    repo: FromDishka[Neo4jGraphRepository],
) -> GraphNodeResponse:
    return await repo.create_node(payload)


@router.patch("/nodes/{node_id}", response_model=GraphNodeResponse)
@inject
async def update_node(
    node_id: str,
    payload: GraphNodeUpdate,
    repo: FromDishka[Neo4jGraphRepository],
) -> GraphNodeResponse:
    return await repo.update_node(node_id, payload)


@router.delete("/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_node(
    node_id: str,
    repo: FromDishka[Neo4jGraphRepository],
) -> None:
    await repo.delete_node(node_id)


@router.post("/edges", response_model=GraphEdgeResponse, status_code=status.HTTP_201_CREATED)
@inject
async def create_edge(
    payload: GraphEdgeCreate,
    repo: FromDishka[Neo4jGraphRepository],
) -> GraphEdgeResponse:
    return await repo.create_edge(payload)


@router.patch("/edges/{edge_id}", response_model=GraphEdgeResponse)
@inject
async def update_edge(
    edge_id: str,
    payload: GraphEdgeUpdate,
    repo: FromDishka[Neo4jGraphRepository],
) -> GraphEdgeResponse:
    return await repo.update_edge(edge_id, payload)


@router.delete("/edges/{edge_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_edge(
    edge_id: str,
    repo: FromDishka[Neo4jGraphRepository],
) -> None:
    await repo.delete_edge(edge_id)


@router.get("/facts/{fact_id}/history", response_model=list[FactRevisionResponse])
@inject
async def list_fact_history(
    fact_id: str,
    repo: FromDishka[Neo4jGraphRepository],
) -> list[FactRevisionResponse]:
    return await repo.list_fact_revisions(fact_id)
