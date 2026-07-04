"""Input / output DTOs for the ask-question use case."""

from pydantic import BaseModel, ConfigDict, Field

from nlp.query.schemas import QuerySpec, SynthesisResponse


class AskQuestionCommand(BaseModel):
    """A natural-language question submitted by the user."""

    model_config = ConfigDict(frozen=True)

    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=10, ge=1, le=50)


class AskQuestionResponse(BaseModel):
    """Structured answer returned to the client."""

    model_config = ConfigDict(frozen=True)

    question: str
    query_spec: QuerySpec
    synthesis: SynthesisResponse
