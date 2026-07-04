"""Hybrid retrieval engine: vector + graph + numeric merge."""

from __future__ import annotations

from typing import Any

from nlp.query.retrieval.neo4j_client import Neo4jClient
from nlp.query.retrieval.qdrant_client import QdrantSearchClient
from nlp.query.schemas import QuerySpec


class HybridRetrievalEngine:
    """Orchestrates vector, graph, and numeric search with RRF merge."""

    def __init__(
        self,
        neo4j: Neo4jClient,
        qdrant: QdrantSearchClient,
        k: int = 60,
        weights: dict[str, float] | None = None,
    ) -> None:
        self._neo4j = neo4j
        self._qdrant = qdrant
        self._k = k
        self._weights = weights or {"qdrant": 1.0, "neo4j": 1.2, "numeric": 1.5}

    async def retrieve(
        self,
        query_vector: list[float],
        spec: QuerySpec,
        limit: int = 20,
    ) -> list[dict]:
        """Execute hybrid retrieval and return merged ranked results."""
        # Parallel search (in real async would use asyncio.gather)
        vector_results = self._qdrant.search(query_vector, spec, limit=limit * 2)
        graph_results = await self._neo4j.search_graph(spec, limit=limit * 2)

        # Build ranked lists for RRF
        ranked_lists = self._build_ranked_lists(vector_results, graph_results)

        # Keep the original per-id metadata (title/year/geography/confidence/
        # span/extracted_at/text) so it survives the RRF merge -- otherwise
        # synthesis receives bare {id, rrf_score, sources} and can't cite
        # anything properly (confirmed missing: metadata was being dropped
        # here before reaching SynthesisEngine).
        metadata_by_id: dict[str, dict] = {}
        for r in vector_results:
            metadata_by_id[str(r["id"])] = r
        for r in graph_results:
            if r.get("name"):
                metadata_by_id.setdefault(r["name"], {}).update(r)

        # RRF merge
        merged = self._reciprocal_rank_fusion(ranked_lists, limit)
        for item in merged:
            meta = metadata_by_id.get(item["id"], {})
            item["finding_text"] = meta.get("text") or item["id"]
            item["source_title"] = meta.get("source_title")
            item["source_year"] = meta.get("source_year")
            item["source_geography"] = meta.get("source_geo")
            item["finding_confidence"] = meta.get("confidence")
            item["span"] = meta.get("span")
            item["extracted_at"] = meta.get("extracted_at")
        return merged

    def _build_ranked_lists(
        self,
        vector_results: list[dict],
        graph_results: list[dict],
    ) -> dict[str, list[str]]:
        """Convert raw results to ranked lists of document IDs."""
        lists: dict[str, list[str]] = {}

        # Qdrant ranked by cosine score (descending)
        lists["qdrant"] = [str(r["id"]) for r in vector_results]

        # Neo4j ranked by confidence (descending) then year
        sorted_graph = sorted(
            graph_results,
            key=lambda x: (
                {"high": 3, "medium": 2, "low": 1}.get(x.get("confidence"), 0),
                x.get("source_year") or 0,
            ),
            reverse=True,
        )
        lists["neo4j"] = [r["name"] for r in sorted_graph if r.get("name")]

        # Numeric results are embedded in neo4j results (Measurement nodes)
        # For separate numeric ranking, we could filter graph results
        lists["numeric"] = [
            r["name"]
            for r in sorted_graph
            if r.get("name") and any(k in r for k in ("min", "max", "value"))
        ]

        return lists

    def _reciprocal_rank_fusion(
        self,
        ranked_lists: dict[str, list[str]],
        limit: int,
    ) -> list[dict]:
        """Merge ranked lists using weighted RRF."""
        scores: dict[str, float] = {}
        metadata: dict[str, dict] = {}

        for source, docs in ranked_lists.items():
            weight = self._weights.get(source, 1.0)
            for rank, doc_id in enumerate(docs, start=1):
                if doc_id not in scores:
                    scores[doc_id] = 0.0
                    metadata[doc_id] = {"sources": []}
                scores[doc_id] += weight / (self._k + rank)
                metadata[doc_id]["sources"].append(source)

        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        return [
            {
                "id": doc_id,
                "rrf_score": score,
                "sources": metadata[doc_id]["sources"],
            }
            for doc_id, score in sorted_results[:limit]
        ]

    async def get_subgraph(
        self,
        node_names: list[str],
        depth: int = 2,
    ) -> list[dict]:
        """Get subgraph for visualization."""
        return await self._neo4j.get_subgraph(node_names, depth)
