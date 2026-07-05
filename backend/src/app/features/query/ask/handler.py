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
from uuid import UUID

from app.domain.interfaces.embedding_generator import IEmbeddingGenerator
from app.domain.interfaces.graph_search import IGraphSearch
from app.domain.interfaces.query_parser import IQueryParser
from app.domain.interfaces.reranker import IReranker
from app.domain.interfaces.synthesis_engine import ISynthesisEngine
from app.domain.interfaces.vector_search import IVectorSearch
from app.features.query.ask.schemas import (
    AnswerSubgraph,
    AskQuestionCommand,
    AskQuestionResponse,
    ExpertRecommendation,
)
from app.features.query.history.repository import AnswersRepository
from nlp.query.schemas import QuerySpec, build_compare_specs

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
        answers_repository: AnswersRepository,
    ) -> None:
        self._parser = parser
        self._graph_search = graph_search
        self._vector_search = vector_search
        self._reranker = reranker
        self._synthesis_engine = synthesis_engine
        self._embedding_generator = embedding_generator
        self._answers_repository = answers_repository

    async def __call__(
        self,
        command: AskQuestionCommand,
        *,
        persist_as: UUID | None = None,
    ) -> AskQuestionResponse:
        """Run the ask pipeline.

        `persist_as`: if set, updates an existing answer row (regenerate flow);
        otherwise inserts a new row. Persistence failures are non-fatal — the
        synthesized answer is still returned to the caller.
        """
        # 1. Parse the natural-language question, then let any explicit UI
        # filters override the parsed values (see _apply_filter_overrides).
        query_spec = self._parser.parse(command.question)
        query_spec = self._apply_filter_overrides(query_spec, command)
        logger.info(
            "parsed query",
            extra={
                "intent": query_spec.intent,
                "materials": query_spec.materials,
                "processes": query_spec.processes,
            },
        )

        # 2-5. Retrieve + rerank. Compare intent ("«отечественная практика» vs
        # «мировая практика»", "«вариант А» vs «вариант Б»") runs retrieval
        # twice, once per side, and tags each result with which side it came
        # from -- a single unscoped query can't be relied on to surface both
        # sides, and even when it does, synthesis has no signal for which
        # finding belongs to which side of the comparison.
        compare_specs = build_compare_specs(query_spec)
        if compare_specs is not None:
            side_a, side_b = compare_specs
            half_k = max(command.top_k // 2, 1)
            results_a = await self._retrieve_and_rerank(command.question, side_a, half_k)
            results_b = await self._retrieve_and_rerank(command.question, side_b, half_k)
            for r in results_a:
                r["compare_side"] = "A"
            for r in results_b:
                r["compare_side"] = "B"
            logger.info(
                "compare retrieval", extra={"side_a_count": len(results_a), "side_b_count": len(results_b)}
            )
            reranked_results = results_a + results_b
        else:
            reranked_results = await self._retrieve_and_rerank(
                command.question, query_spec, command.top_k
            )

        # 6. Synthesize an answer
        synthesis = self._synthesis_engine.synthesize(command.question, reranked_results)

        # 7. Fetch a subgraph around the matched entries for the answer canvas.
        # Non-fatal: if this fails we still return the synthesized answer with
        # an empty graph rather than 500-ing the whole request.
        try:
            subgraph_data = await self._graph_search.fetch_subgraph(query_spec)
            subgraph = AnswerSubgraph(**subgraph_data)
        except Exception as exc:
            logger.warning("subgraph fetch failed", extra={"error": str(exc)})
            subgraph = AnswerSubgraph()

        # 7b. Graph-grounded "who knows this" — experts/labs tied to the query's
        # entities via authored/validated edges (case-spec "носители экспертизы").
        entity_names = [
            *query_spec.materials,
            *query_spec.processes,
            *query_spec.topics,
            *query_spec.equipment,
        ]
        graph_experts = await self._graph_search.recommend_experts(entity_names, limit=8)

        # Fold the graph-grounded experts into synthesis.experts (normalized to
        # {name, affiliation}) so the answer's "Эксперты" card is populated from
        # the who-authored-what graph, not just whatever the synthesis LLM
        # happened to echo (which is usually empty). Persisted + returned in one
        # place, so saved answers show them too.
        synthesis = synthesis.model_copy(
            update={"experts": self._merge_experts(synthesis.experts, graph_experts)}
        )

        # 8. Persist. Regenerate path updates the existing row; new ask inserts.
        answer_id: UUID | None = persist_as
        try:
            spec_dump = query_spec.model_dump(mode="json")
            synth_dump = synthesis.model_dump(mode="json")
            subgraph_dump = subgraph.model_dump(mode="json")
            confidence = synth_dump.get("confidence")
            if persist_as is not None:
                await self._answers_repository.update(
                    persist_as,
                    query_spec=spec_dump,
                    synthesis=synth_dump,
                    subgraph=subgraph_dump,
                    confidence=confidence,
                )
            else:
                record = await self._answers_repository.create(
                    question=command.question,
                    query_spec=spec_dump,
                    synthesis=synth_dump,
                    subgraph=subgraph_dump,
                    confidence=confidence,
                )
                answer_id = record.id
        except Exception as exc:
            logger.warning("answer persistence failed", extra={"error": str(exc)})

        return AskQuestionResponse(
            id=answer_id,
            question=command.question,
            query_spec=query_spec,
            synthesis=synthesis,
            subgraph=subgraph,
            graph_experts=[ExpertRecommendation(**e) for e in graph_experts],
        )

    @staticmethod
    def _merge_experts(
        llm_experts: list[dict[str, Any]],
        graph_experts: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Normalize + merge synthesis-LLM experts and graph-grounded experts.

        Both are reduced to the {name, affiliation} shape the answer UI reads.
        Graph experts lead (they're grounded in authored/validated edges);
        deduplicated by case-insensitive name; capped so the card stays compact.
        """
        merged: list[dict[str, Any]] = []
        seen: set[str] = set()

        def add(name: Any, affiliation: Any) -> None:
            name = str(name or "").strip()
            if not name:
                return
            key = name.lower()
            if key in seen:
                return
            seen.add(key)
            merged.append({"name": name, "affiliation": str(affiliation or "").strip()})

        for e in graph_experts or []:
            context = e.get("context") or []
            affiliation = (
                e.get("email")
                or (", ".join(str(c) for c in context if c) if context else "")
                or (f"{e.get('n_publications', 0)} публикаций" if e.get("n_publications") else "")
            )
            add(e.get("expert"), affiliation)

        for e in llm_experts or []:
            add(e.get("name"), e.get("affiliation") or e.get("expertise"))

        return merged[:8]

    def _apply_filter_overrides(
        self, spec: QuerySpec, command: AskQuestionCommand
    ) -> QuerySpec:
        """Override parser-inferred fields with explicit filters from the UI.

        Only fields the user actually set are overridden; everything else keeps
        the value the parser inferred from the question text.
        """
        updates: dict[str, Any] = {}
        if command.materials:
            updates["materials"] = command.materials
        if command.processes:
            updates["processes"] = command.processes
        if command.geography is not None:
            updates["geography"] = command.geography
        if command.year_from is not None or command.year_to is not None:
            time_update: dict[str, Any] = {}
            if command.year_from is not None:
                time_update["from_year"] = command.year_from
            if command.year_to is not None:
                time_update["to_year"] = command.year_to
            updates["time_range"] = spec.time_range.model_copy(update=time_update)
        if not updates:
            return spec
        return spec.model_copy(update=updates)

    async def _retrieve_and_rerank(
        self, question: str, spec: QuerySpec, top_k: int
    ) -> list[dict[str, Any]]:
        """Graph search + vector search + dedup-merge + cross-encoder rerank
        for a single QuerySpec. Shared by the normal path and by each side of
        a compare-intent query (see build_compare_specs)."""
        graph_results = await self._graph_search.search(spec, limit=top_k)
        vector_results = await self._vector_search_with_embedding(question, spec, top_k)
        merged_results = self._merge_results(graph_results, vector_results)
        return self._reranker.rerank(question, merged_results, top_k=top_k)

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

    @staticmethod
    def _result_key(r: dict[str, Any]) -> tuple[str, Any]:
        """Stable identity of a retrieved finding for dedup.

        Deliberately NOT doc_id: a single source document contributes many
        distinct findings, so deduping by doc_id collapses them to one and
        throws away most of the semantic hits. Key on the entity / finding
        text instead so every distinct finding survives, and a graph hit that
        matches the same entity as a vector hit is recognised as a duplicate.
        """
        eids = r.get("entity_ids")
        if eids:
            return ("e", tuple(sorted(str(e) for e in eids)))
        text = r.get("text") or r.get("finding_text")
        if text:
            return ("t", text)
        return ("d", r.get("doc_id") or r.get("id"))

    def _merge_results(
        self,
        graph_results: list[dict[str, Any]],
        vector_results: list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        """Merge vector and graph candidates, vector-first, deduped by finding.

        Vector (semantic) candidates lead: the cross-encoder reranker is a
        no-op in this environment (torch/onnxruntime unavailable -> identity
        passthrough that just truncates to top_k), so ordering here IS the
        final ordering. Graph-first ordering therefore let low-relevance
        structured hits (often relation-type labels like "removes_metals" with
        no doc_id) fill every slot and starve the far more relevant vector
        hits, which is exactly the "finds nothing" symptom. Lead with the
        scored semantic hits and let graph results backfill the remainder.
        """
        merged: list[dict[str, Any]] = []
        seen: set[tuple[str, Any]] = set()
        # Normalize vector candidates to the shape synthesis/format_findings
        # expects (finding_text, not text) so they render in the prompt.
        normalized_vectors = [
            {**r, "finding_text": r.get("text") or r.get("finding_text", "")}
            for r in (vector_results or [])
        ]
        for r in [*normalized_vectors, *graph_results]:
            key = self._result_key(r)
            if key in seen:
                continue
            seen.add(key)
            merged.append(r)
        return merged
