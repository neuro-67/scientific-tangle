"""Chunk text and upload embeddings to Qdrant.

Usage:
    python -m nlp.ingestion.qdrant_upload nlp/pdftest_graph.json nlp/test_graph.json

Requires QDRANT_HOST, QDRANT_PORT env vars (or uses defaults).
"""

from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from nlp.embeddings.bge_m3 import BgeEmbeddingGenerator
from nlp.ingestion.node_text import build_node_text

logger = logging.getLogger(__name__)

_COLLECTION = "chunks"
_VECTOR_SIZE = 1024  # BAAI/bge-m3 (RouterAI)


def _get_qdrant_client() -> QdrantClient:
    host = os.environ.get("QDRANT_HOST", "localhost")
    port = int(os.environ.get("QDRANT_PORT", "6333"))
    return QdrantClient(host=host, port=port)


def _ensure_collection(client: QdrantClient) -> None:
    """Create collection if it doesn't exist."""
    try:
        client.get_collection(_COLLECTION)
        logger.info("collection exists", extra={"collection": _COLLECTION})
    except Exception:
        logger.info("creating collection", extra={"collection": _COLLECTION})
        client.create_collection(
            collection_name=_COLLECTION,
            vectors_config=VectorParams(size=_VECTOR_SIZE, distance=Distance.COSINE),
        )


def _extract_chunks(graph_path: str) -> list[dict[str, Any]]:
    """Extract text chunks from a graph JSON file."""
    with open(graph_path, encoding="utf-8") as f:
        data = json.load(f)

    chunks = []
    for node in data.get("nodes", []):
        node_id = node.get("id", "")
        label = node.get("label", "")
        props = node.get("properties", {})

        # Fold the node's meaningful attributes into the embedded text, not just
        # id + description (see nlp/ingestion/node_text.py).
        text = build_node_text(node_id, label, props)

        chunks.append({
            "id": str(uuid.uuid4()),
            "text": text,
            "entity_id": node_id,
            "entity_type": label,
            "source_document": data.get("document", graph_path),
            "properties": props,
        })

    return chunks


def upload_graph(graph_path: str, client: QdrantClient, generator: BgeEmbeddingGenerator) -> int:
    """Upload chunks from a graph to Qdrant."""
    chunks = _extract_chunks(graph_path)
    logger.info("extracted chunks", extra={"path": graph_path, "count": len(chunks)})

    if not chunks:
        return 0

    # Generate embeddings
    texts = [c["text"] for c in chunks]
    embeddings = generator.encode_batch(texts)

    # Build points
    points = []
    for chunk, embedding in zip(chunks, embeddings):
        points.append(
            PointStruct(
                id=chunk["id"],
                vector=embedding,
                payload={
                    "text": chunk["text"],
                    "entity_id": chunk["entity_id"],
                    "entity_type": chunk["entity_type"],
                    "source_document": chunk["source_document"],
                    "doc_id": chunk["source_document"],  # alias read by QdrantSearchClient
                    # unprefixed so geography/year payload filters in QdrantSearchClient match;
                    # prop_-prefixed kept too for backward compat with any existing readers
                    **chunk["properties"],
                    **{f"prop_{k}": v for k, v in chunk["properties"].items()},
                },
            )
        )

    # Upload to Qdrant
    client.upsert(collection_name=_COLLECTION, points=points)
    logger.info("uploaded chunks", extra={"path": graph_path, "count": len(points)})

    return len(points)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python -m nlp.ingestion.qdrant_upload <graph.json> [graph2.json ...]")
        sys.exit(1)

    client = _get_qdrant_client()
    _ensure_collection(client)

    generator = BgeEmbeddingGenerator()

    total = 0
    for path in sys.argv[1:]:
        count = upload_graph(path, client, generator)
        total += count
        print(f"\nUploaded {path}: {count} chunks")

    print(f"\nTotal chunks uploaded: {total}")


if __name__ == "__main__":
    main()
