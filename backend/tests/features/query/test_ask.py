"""Tests for the query/ask feature slice."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.domain.interfaces.embedding_generator import IEmbeddingGenerator
from app.domain.interfaces.graph_search import IGraphSearch
from app.domain.interfaces.query_parser import IQueryParser
from app.domain.interfaces.reranker import IReranker
from app.domain.interfaces.synthesis_engine import ISynthesisEngine
from app.domain.interfaces.vector_search import IVectorSearch
from app.features.query.ask.handler import AskQuestionHandler
from app.features.query.ask.schemas import AskQuestionCommand, AskQuestionResponse
from app.features.query.history.schemas import AnswerRecord
from nlp.query.schemas import QuerySpec, SynthesisResponse


class FakeQueryParser(IQueryParser):
    """Returns a fixed QuerySpec for testing."""

    def __init__(self, spec: QuerySpec | None = None) -> None:
        self._spec = spec or QuerySpec()

    def parse(self, question: str) -> QuerySpec:
        return self._spec


class FakeSynthesisEngine(ISynthesisEngine):
    """Returns a fixed synthesis for testing."""

    def synthesize(self, question: str, findings: list[dict]) -> SynthesisResponse:
        return SynthesisResponse(
            answer="Тестовый ответ",
            consensus=["Тестовый консенсус"],
            sources=[],
            confidence="high",
        )


class FakeVectorSearch(IVectorSearch):
    """Returns canned results for testing."""

    async def search(self, query_vector, spec, limit=20):
        return []

    async def health(self):
        return True


class FakeReranker(IReranker):
    """Identity reranker for testing."""

    def rerank(self, query: str, results: list[dict], top_k: int = 10) -> list[dict]:
        return results[:top_k]


class FakeEmbeddingGenerator(IEmbeddingGenerator):
    """Returns zero vectors for testing."""

    def encode(self, text: str) -> list[float]:
        return [0.0] * 1024


class FakeGraphSearch(IGraphSearch):
    """Returns canned results for testing."""

    def __init__(self, results: list[dict] | None = None) -> None:
        self._results = results or []

    async def search(self, spec: QuerySpec, limit: int = 20) -> list[dict]:
        return self._results

    async def get_entity_context(self, entity_name: str, entity_type: str) -> dict | None:
        return None

    async def fetch_subgraph(self, spec: QuerySpec, node_limit: int = 30) -> dict:
        return {"nodes": [], "edges": []}


class FakeAnswersRepository:
    """Records create/update calls in memory instead of hitting Postgres."""

    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []
        self.updated: list[dict[str, Any]] = []

    async def create(
        self,
        *,
        question: str,
        query_spec: dict[str, Any],
        synthesis: dict[str, Any],
        subgraph: dict[str, Any],
        confidence: str | None,
    ) -> AnswerRecord:
        self.created.append({"question": question})
        now = datetime.now(tz=timezone.utc)
        return AnswerRecord(
            id=uuid4(),
            question=question,
            query_spec=query_spec,
            synthesis=synthesis,
            subgraph=subgraph,
            confidence=confidence,
            created_at=now,
            updated_at=now,
        )

    async def update(
        self,
        answer_id: UUID,
        *,
        query_spec: dict[str, Any],
        synthesis: dict[str, Any],
        subgraph: dict[str, Any],
        confidence: str | None,
    ) -> AnswerRecord | None:
        self.updated.append({"id": answer_id})
        return None


@pytest.fixture
def handler() -> AskQuestionHandler:
    spec = QuerySpec(
        materials=["вода"],
        processes=["обессоливание"],
        intent="review",
    )
    results = [
        {
            "finding_text": "Обратный осмос эффективен для удаления солей.",
            "source_title": "Водоподготовка 2023",
            "source_year": 2023,
            "finding_confidence": 0.85,
        }
    ]
    return AskQuestionHandler(
        parser=FakeQueryParser(spec),
        graph_search=FakeGraphSearch(results),
        vector_search=FakeVectorSearch(),
        reranker=FakeReranker(),
        synthesis_engine=FakeSynthesisEngine(),
        embedding_generator=FakeEmbeddingGenerator(),
        answers_repository=FakeAnswersRepository(),
    )


@pytest.mark.anyio
async def test_ask_question_returns_structured_response(handler: AskQuestionHandler) -> None:
    command = AskQuestionCommand(question="методы обессоливания воды", top_k=5)
    response = await handler(command)

    assert isinstance(response, AskQuestionResponse)
    assert response.question == command.question
    assert response.query_spec.materials == ["вода"]
    assert response.query_spec.processes == ["обессоливание"]
    assert isinstance(response.synthesis, SynthesisResponse)
    assert response.synthesis.answer
    assert response.synthesis.confidence is not None


@pytest.mark.anyio
async def test_ask_question_no_results() -> None:
    handler = AskQuestionHandler(
        parser=FakeQueryParser(QuerySpec()),
        graph_search=FakeGraphSearch([]),
        vector_search=FakeVectorSearch(),
        reranker=FakeReranker(),
        synthesis_engine=FakeSynthesisEngine(),
        embedding_generator=FakeEmbeddingGenerator(),
        answers_repository=FakeAnswersRepository(),
    )
    command = AskQuestionCommand(question="несуществующий запрос", top_k=5)
    response = await handler(command)

    assert response.synthesis.answer == "Тестовый ответ"
    assert response.synthesis.confidence == "high"
