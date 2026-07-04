"""Input / output DTOs for the ask-question use case."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from nlp.query.schemas import Geography, QuerySpec, SynthesisResponse


class SubgraphNode(BaseModel):
    id: str
    label: str
    type: str
    revision_count: int = 0


class SubgraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    label: str | None = None


class AnswerSubgraph(BaseModel):
    nodes: list[SubgraphNode] = []
    edges: list[SubgraphEdge] = []


class AskQuestionCommand(BaseModel):
    """A natural-language question submitted by the user.

    The search UI can pass explicit structured filters alongside the free-text
    question (materials/processes/geography/year window). When present they
    override whatever the parser inferred from the question text, so the
    multi-level filtering + RU-vs-foreign controls in the frontend actually
    scope retrieval instead of being decorative.
    """

    model_config = ConfigDict(frozen=True)

    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=10, ge=1, le=50)

    materials: list[str] | None = None
    processes: list[str] | None = None
    geography: Geography | None = None
    year_from: int | None = None
    year_to: int | None = None


class AskQuestionResponse(BaseModel):
    """Structured answer returned to the client."""

    model_config = ConfigDict(frozen=True)

    id: UUID | None = None
    question: str
    query_spec: QuerySpec
    synthesis: SynthesisResponse
    subgraph: AnswerSubgraph = AnswerSubgraph()
