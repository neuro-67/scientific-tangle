"""Bridges the process-document worker task to the ML-1 ingestion pipeline.

nlp/run_corpus_test.py and nlp/ingestion/* are synchronous (threaded LLM
calls, sync Neo4j driver, sync Qdrant client) -- the whole thing runs in a
worker thread via asyncio.to_thread so it never blocks the arq event loop.
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Any

_EXTENSION_BY_CONTENT_TYPE = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}


def _guess_suffix(filename: str, content_type: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in (".pdf", ".docx"):
        return suffix
    return _EXTENSION_BY_CONTENT_TYPE.get(content_type, ".pdf")


def _run_pipeline_sync(file_bytes: bytes, filename: str, content_type: str) -> dict[str, Any]:
    from nlp.embeddings.bge_m3 import BgeEmbeddingGenerator
    from nlp.ingestion.neo4j_import import _get_neo4j_driver, import_graph
    from nlp.ingestion.qdrant_upload import _ensure_collection, _get_qdrant_client, upload_graph
    from nlp.run_corpus_test import drop_unverified_measurements, process_document

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        src_path = tmp_dir / f"upload{_guess_suffix(filename, content_type)}"
        src_path.write_bytes(file_bytes)

        stats = process_document(src_path, tmp_dir)

        graph_path = Path(stats["output_file"])
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        graph["document"] = filename
        clean = drop_unverified_measurements(graph)
        clean_path = tmp_dir / "clean_graph.json"
        clean_path.write_text(json.dumps(clean, ensure_ascii=False), encoding="utf-8")

        driver = _get_neo4j_driver()
        try:
            neo4j_stats = import_graph(str(clean_path), driver)
        finally:
            driver.close()

        qdrant_client = _get_qdrant_client()
        _ensure_collection(qdrant_client)
        n_chunks = upload_graph(str(clean_path), qdrant_client, BgeEmbeddingGenerator())

        return {
            **stats,
            "dropped_unverified_measurements": len(graph["nodes"]) - len(clean["nodes"]),
            "neo4j": neo4j_stats,
            "qdrant_chunks_uploaded": n_chunks,
        }


async def run_ingestion_pipeline(file_bytes: bytes, filename: str, content_type: str) -> dict[str, Any]:
    """Parse -> chunk -> extract -> normalize -> write to Neo4j + Qdrant."""
    return await asyncio.to_thread(_run_pipeline_sync, file_bytes, filename, content_type)
