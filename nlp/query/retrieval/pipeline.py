"""End-to-end query pipeline: parse → retrieve → rerank → synthesize."""

from __future__ import annotations

from nlp.query.parser import QuerySpecParser
from nlp.query.retrieval.engine import HybridRetrievalEngine
from nlp.query.retrieval.reranker import CrossEncoderReranker
from nlp.query.retrieval.synthesis import SynthesisEngine
from nlp.query.schemas import QuerySpec, SynthesisResponse


class QueryPipeline:
    """Full ML-2 query pipeline."""

    def __init__(
        self,
        parser: QuerySpecParser | None = None,
        retrieval: HybridRetrievalEngine | None = None,
        reranker: CrossEncoderReranker | None = None,
        synthesis: SynthesisEngine | None = None,
    ) -> None:
        self._parser = parser or QuerySpecParser()
        self._retrieval = retrieval
        self._reranker = reranker
        self._synthesis = synthesis or SynthesisEngine(self._parser)

    async def answer(self, question: str, query_vector: list[float]) -> dict:
        """End-to-end: question → answer."""
        # 1. Parse
        spec = self._parser.parse(question)

        # 2. Retrieve
        if self._retrieval is None:
            raise RuntimeError("Retrieval engine not configured")
        candidates = await self._retrieval.retrieve(query_vector, spec, limit=20)

        # 3. Rerank (optional)
        if self._reranker and candidates:
            # Extract text from candidates for reranking
            texts = [c.get("text", "") for c in candidates if c.get("text")]
            if texts:
                ranked = self._reranker.rerank(question, texts)
                # Reorder candidates by rerank score
                text_to_candidate = {c.get("text", ""): c for c in candidates}
                candidates = [
                    {**text_to_candidate.get(t, {}), "rerank_score": s}
                    for t, s in ranked
                    if t in text_to_candidate
                ]

        # 4. Synthesize
        response = self._synthesis.synthesize(question, candidates)

        # 5. Subgraph (optional)
        node_names = [c.get("id") for c in candidates[:5] if c.get("id")]
        subgraph = []
        if self._retrieval and node_names:
            subgraph = await self._retrieval.get_subgraph(node_names, depth=2)

        return {
            "query_spec": spec.model_dump(by_alias=True),
            "candidates_count": len(candidates),
            "answer": response.model_dump(by_alias=True),
            "subgraph": subgraph,
        }
