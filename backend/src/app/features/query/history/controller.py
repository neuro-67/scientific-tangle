"""HTTP routes for answer history: list, get, delete, regenerate,
plus answer-scoped graph mutations that keep the snapshot in sync with Neo4j."""

from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Query, status

from app.features.graph.schemas import (
    GraphEdgeCreate,
    GraphEdgeResponse,
    GraphEdgeUpdate,
    GraphNodeCreate,
    GraphNodeResponse,
    GraphNodeUpdate,
)
from app.features.query.ask.schemas import AskQuestionResponse
from app.features.query.history.handler import (
    DeleteAnswerHandler,
    GetAnswerHandler,
    ListAnswersHandler,
    ListAnswersQuery,
    RegenerateAnswerHandler,
)
from app.features.query.history.mutations import AnswerGraphMutations
from app.features.query.history.schemas import AnswerListItem, AnswerRecord

router = APIRouter(tags=["answers"])


@router.get(
    "/answers",
    response_model=list[AnswerListItem],
    status_code=status.HTTP_200_OK,
    summary="List saved answers",
)
@inject
async def list_answers(
    handler: FromDishka[ListAnswersHandler],
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[AnswerListItem]:
    return await handler(ListAnswersQuery(limit=limit, offset=offset))


@router.get(
    "/answers/{answer_id}",
    response_model=AnswerRecord,
    status_code=status.HTTP_200_OK,
    summary="Get a saved answer with the full envelope",
)
@inject
async def get_answer(
    answer_id: UUID,
    handler: FromDishka[GetAnswerHandler],
) -> AnswerRecord:
    return await handler(answer_id)


@router.delete(
    "/answers/{answer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a saved answer",
)
@inject
async def delete_answer(
    answer_id: UUID,
    handler: FromDishka[DeleteAnswerHandler],
) -> None:
    await handler(answer_id)


@router.post(
    "/answers/{answer_id}/nodes",
    response_model=GraphNodeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a node in Neo4j and append it to this answer's snapshot",
)
@inject
async def create_answer_node(
    answer_id: UUID,
    payload: GraphNodeCreate,
    mutations: FromDishka[AnswerGraphMutations],
) -> GraphNodeResponse:
    return await mutations.create_node(answer_id, payload)


@router.patch(
    "/answers/{answer_id}/nodes/{node_id}",
    response_model=GraphNodeResponse,
    summary="Update a node in Neo4j and mirror the change on this answer's snapshot",
)
@inject
async def update_answer_node(
    answer_id: UUID,
    node_id: str,
    payload: GraphNodeUpdate,
    mutations: FromDishka[AnswerGraphMutations],
) -> GraphNodeResponse:
    return await mutations.update_node(answer_id, node_id, payload)


@router.delete(
    "/answers/{answer_id}/nodes/{node_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a node in Neo4j and remove it from this answer's snapshot",
)
@inject
async def delete_answer_node(
    answer_id: UUID,
    node_id: str,
    mutations: FromDishka[AnswerGraphMutations],
) -> None:
    await mutations.delete_node(answer_id, node_id)


@router.post(
    "/answers/{answer_id}/edges",
    response_model=GraphEdgeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an edge in Neo4j and append it to this answer's snapshot",
)
@inject
async def create_answer_edge(
    answer_id: UUID,
    payload: GraphEdgeCreate,
    mutations: FromDishka[AnswerGraphMutations],
) -> GraphEdgeResponse:
    return await mutations.create_edge(answer_id, payload)


@router.patch(
    "/answers/{answer_id}/edges/{edge_id}",
    response_model=GraphEdgeResponse,
    summary="Update an edge in Neo4j and mirror the change on this answer's snapshot",
)
@inject
async def update_answer_edge(
    answer_id: UUID,
    edge_id: str,
    payload: GraphEdgeUpdate,
    mutations: FromDishka[AnswerGraphMutations],
) -> GraphEdgeResponse:
    return await mutations.update_edge(answer_id, edge_id, payload)


@router.delete(
    "/answers/{answer_id}/edges/{edge_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an edge in Neo4j and remove it from this answer's snapshot",
)
@inject
async def delete_answer_edge(
    answer_id: UUID,
    edge_id: str,
    mutations: FromDishka[AnswerGraphMutations],
) -> None:
    await mutations.delete_edge(answer_id, edge_id)


@router.post(
    "/answers/{answer_id}/regenerate",
    response_model=AskQuestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Re-run the pipeline over the saved question and update the row",
)
@inject
async def regenerate_answer(
    answer_id: UUID,
    handler: FromDishka[RegenerateAnswerHandler],
) -> AskQuestionResponse:
    return await handler(answer_id)
