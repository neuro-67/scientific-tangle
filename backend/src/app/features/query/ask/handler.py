"""Ask-question use case: parse → hybrid search → synthesize → respond.

This is the orchestrator for the ML-2 query pipeline. It delegates to:
- IQueryParser    (YandexGPT/RouterAI) to turn natural language into QuerySpec
- IGraphSearch    (Neo4j)     to retrieve structured findings from the graph
- IVectorSearch   (Qdrant)    to retrieve semantically similar chunks
- IReranker       (cross-encoder) to score merged candidates by relevance
- ISynthesisEngine (YandexGPT/RouterAI) to synthesize a structured answer

Graph and vector candidates are concatenated (deduplicated) and handed to the
cross-encoder reranker, which scores them against the actual query text.
This replaces an earlier RRF (Reciprocal Rank Fusion) merge step: RRF only
fuses rank *positions* from each retrieval branch and cannot see relevance,
whereas the cross-encoder scores real semantic relevance -- and is a
requirement of its own (docs/ROADMAP.md P2: "cross-encoder реранк вместо RRF").
"""

from __future__ import annotations

import logging
from typing import Any

from app.domain.interfaces.embedding_generator import IEmbeddingGenerator
from app.domain.interfaces.graph_search import IGraphSearch
from app.domain.interfaces.query_parser import IQueryParser
from app.domain.interfaces.reranker import IReranker
from app.domain.interfaces.synthesis_engine import ISynthesisEngine
from app.domain.interfaces.vector_search import IVectorSearch
from app.features.query.ask.schemas import AskQuestionCommand, AskQuestionResponse
from nlp.query.schemas import QuerySpec

logger = logging.getLogger(__name__)


class AskQuestionHandler:
    """Orchestrates the full query-answer pipeline with hybrid retrieval."""

    def __init__(
        self,
        parser: IQueryParser,
        graph_search: IGraphSearch,
        vector_search: IVectorSearch,
        reranker: IReranker,
        synthesis_engine: ISynthesisEngine,
        embedding_generator: IEmbeddingGenerator,
    ) -> None:
        self._parser = parser
        self._graph_search = graph_search
        self._vector_search = vector_search
        self._reranker = reranker
        self._synthesis_engine = synthesis_engine
        self._embedding_generator = embedding_generator

    async def __call__(self, command: AskQuestionCommand) -> AskQuestionResponse:
        # 1. Parse the natural-language question
        query_spec = self._parser.parse(command.question)
        logger.info(
            "parsed query",
            extra={
                "intent": query_spec.intent,
                "materials": query_spec.materials,
                "processes": query_spec.processes,
            },
        )

        # 2. Search the knowledge graph (structured)
        graph_results = await self._graph_search.search(query_spec, limit=command.top_k)
        logger.info("graph results", extra={"count": len(graph_results)})

        # 3. Search Qdrant (semantic) using generated embedding
        vector_results = await self._vector_search_with_embedding(command.question, query_spec, command.top_k)
        if vector_results:
            logger.info("vector results", extra={"count": len(vector_results)})

        # 4. Merge candidates (dedup only -- ranking is the reranker's job, next step)
        merged_results = self._merge_results(graph_results, vector_results)
        logger.info("merged results", extra={"count": len(merged_results)})

        # 5. Rerank with cross-encoder
        reranked_results = self._reranker.rerank(
            command.question, merged_results, top_k=command.top_k
        )
        logger.info("reranked results", extra={"count": len(reranked_results)})

        # 6. Synthesize an answer
        synthesis = self._synthesis_engine.synthesize(command.question, reranked_results)

        return AskQuestionResponse(
            question=command.question,
            query_spec=query_spec,
            synthesis=synthesis,
        )

    async def _vector_search_with_embedding(
        self, question: str, spec: QuerySpec, limit: int
    ) -> list[dict[str, Any]] | None:
        """Generate embedding and search Qdrant; return None if unavailable."""
        try:
            embedding = self._embedding_generator.encode(question)
            # Skip if we got zero vector (model not loaded)
            if all(v == 0.0 for v in embedding):
                logger.debug("embedding model not available, skipping vector search")
                return None
            return await self._vector_search.search(embedding, spec, limit=limit)
        except Exception as exc:
            logger.warning("vector search failed", extra={"error": str(exc)})
            return None

    def _merge_results(
        self,
        graph_results: list[dict[str, Any]],
        vector_results: list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        """Concatenate graph and vector candidates, deduplicated by doc_id.

        No RRF scoring: the cross-encoder reranker (self._reranker) scores
        each candidate against the actual query text right after this, which
        is a stronger relevance signal than fusing two branches' rank
        positions without ever looking at the query.
        """
        merged = list(graph_results)
        seen = {r.get("doc_id") for r in merged if r.get("doc_id")}
        for r in vector_results or []:
            doc_id = r.get("doc_id") or r.get("id")
            if doc_id in seen:
                continue
            seen.add(doc_id)
            # Normalize to the shape format_findings()/synthesis expects
            # (finding_text, not text) so vector-only candidates that survive
            # reranking still show up in the synthesis prompt instead of
            # silently rendering as empty lines.
            merged.append({**r, "finding_text": r.get("text") or r.get("finding_text", "")})
        return merged
