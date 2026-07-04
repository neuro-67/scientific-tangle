"""Input / output DTOs for the ask-question use case."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from nlp.query.schemas import Geography, QuerySpec, SynthesisResponse


class SubgraphNode(BaseModel):
    id: str
    label: str
    type: str


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


class ExpertRecommendation(BaseModel):
    """A graph-grounded "who knows this" suggestion for the answer."""

    expert: str
    relevance: int = 0
    email: str | None = None
    n_publications: int = 0
    context: list[str] = []


class AskQuestionResponse(BaseModel):
    """Structured answer returned to the client."""

    model_config = ConfigDict(frozen=True)

    id: UUID | None = None
    question: str
    query_spec: QuerySpec
    synthesis: SynthesisResponse
    subgraph: AnswerSubgraph = AnswerSubgraph()
    # Experts/labs derived from the graph's authored/validated edges for the
    # entities in this query -- distinct from synthesis.experts (LLM-read from
    # the retrieved text). case-specification.md "носители экспертизы".
    graph_experts: list[ExpertRecommendation] = []
