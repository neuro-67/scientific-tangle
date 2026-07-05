"""Re-embed all nodes from Neo4j into Qdrant.

Usage (inside backend container):
    python /app/nlp/reembed.py

Requires: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, QDRANT_HOST, QDRANT_PORT,
          ROUTERAI_API_KEY, ROUTERAI_BASE_URL env vars.
"""

from __future__ import annotations

import logging
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

# Add nlp to path
sys.path.insert(0, "/app")

from nlp.embeddings.bge_m3 import BgeEmbeddingGenerator
from nlp.ingestion.node_text import build_node_text

logger = logging.getLogger(__name__)

_COLLECTION = "chunks"
_VECTOR_SIZE = 1024
_BATCH_SIZE = 32  # Smaller batch for RouterAI stability
_N_WORKERS = 4    # Parallel workers


def _get_neo4j_driver():
    uri = os.environ.get("NEO4J_URI", "bolt://neo4j:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "neo4j_password")
    return GraphDatabase.driver(uri, auth=(user, password))


def _get_qdrant_client() -> QdrantClient:
    host = os.environ.get("QDRANT_HOST", "localhost")
    port = int(os.environ.get("QDRANT_PORT", "6333"))
    return QdrantClient(host=host, port=port)


def _ensure_collection(client: QdrantClient) -> None:
    try:
        client.get_collection(_COLLECTION)
        logger.info("collection exists", extra={"collection": _COLLECTION})
    except Exception:
        logger.info("creating collection", extra={"collection": _COLLECTION})
        client.create_collection(
            collection_name=_COLLECTION,
            vectors_config=VectorParams(size=_VECTOR_SIZE, distance=Distance.COSINE),
        )


def fetch_all_nodes(driver) -> list[dict[str, Any]]:
    """Fetch all nodes from Neo4j with their properties."""
    query = """
    MATCH (n)
    WHERE n.id IS NOT NULL
    RETURN n.id AS node_id, labels(n) AS labels, properties(n) AS props
    """
    with driver.session() as session:
        result = session.run(query)
        nodes = []
        for record in result:
            nodes.append({
                "node_id": record["node_id"],
                "labels": record["labels"],
                "props": dict(record["props"]),
            })
        return nodes


def process_batch(batch: list[dict], generator: BgeEmbeddingGenerator) -> list[PointStruct]:
    """Process a batch of nodes: generate embeddings and build points."""
    texts = []
    for node in batch:
        node_id = node["node_id"]
        labels = node["labels"]
        props = node["props"]
        label = labels[0] if labels else "Node"
        text = build_node_text(node_id, label, props)
        node["_text"] = text
        texts.append(text)
    
    # Generate embeddings with retry logic built into BgeEmbeddingGenerator
    embeddings = generator.encode_batch(texts)
    
    points = []
    for node, embedding in zip(batch, embeddings):
        props = node["props"]
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "text": node["_text"],
                "entity_id": node["node_id"],
                "entity_type": node["labels"][0] if node["labels"] else "Node",
                "source_document": props.get("source_document", ""),
                "doc_id": props.get("source_document", ""),
                **props,
                **{f"prop_{k}": v for k, v in props.items()},
            },
        )
        points.append(point)
    
    return points


def reembed_all():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    
    logger.info("=== Starting re-embedding ===")
    
    # Connect to Neo4j
    driver = _get_neo4j_driver()
    logger.info("connected to Neo4j")
    
    # Connect to Qdrant
    qdrant = _get_qdrant_client()
    _ensure_collection(qdrant)
    logger.info("connected to Qdrant")
    
    # Fetch all nodes
    logger.info("fetching nodes from Neo4j...")
    nodes = fetch_all_nodes(driver)
    total = len(nodes)
    logger.info(f"found {total} nodes to embed")
    
    if total == 0:
        logger.warning("no nodes found in Neo4j")
        return
    
    # Initialize embedding generator
    generator = BgeEmbeddingGenerator()
    
    # Process in batches with parallel workers
    uploaded = 0
    failed_batches = 0
    start_time = time.time()
    
    # Split into batches
    batches = [nodes[i:i + _BATCH_SIZE] for i in range(0, total, _BATCH_SIZE)]
    
    logger.info(f"processing {len(batches)} batches with {_N_WORKERS} workers")
    
    with ThreadPoolExecutor(max_workers=_N_WORKERS) as executor:
        # Submit all batches
        future_to_batch = {
            executor.submit(process_batch, batch, generator): i 
            for i, batch in enumerate(batches)
        }
        
        for future in as_completed(future_to_batch):
            batch_idx = future_to_batch[future]
            try:
                points = future.result()
                if points:
                    qdrant.upsert(collection_name=_COLLECTION, points=points)
                    uploaded += len(points)
                
                # Progress report
                if batch_idx % 10 == 0 or batch_idx == len(batches) - 1:
                    elapsed = time.time() - start_time
                    rate = uploaded / elapsed if elapsed > 0 else 0
                    remaining = (total - uploaded) / rate if rate > 0 else 0
                    logger.info(
                        f"progress: {uploaded}/{total} ({100*uploaded/total:.1f}%) "
                        f"rate={rate:.1f}/s ETA={remaining/60:.1f}min"
                    )
                    
            except Exception as exc:
                failed_batches += 1
                logger.error(f"batch {batch_idx} failed: {exc}")
    
    elapsed = time.time() - start_time
    logger.info(
        f"=== Re-embedding complete: {uploaded}/{total} uploaded, "
        f"{failed_batches} failed batches, {elapsed:.1f}s ==="
    )
    
    # Verify
    try:
        info = qdrant.get_collection(_COLLECTION)
        result = info.dict() if hasattr(info, "dict") else info
        vectors_count = result.get("vectors_count", 0) if isinstance(result, dict) else getattr(result, "vectors_count", 0)
        logger.info(f"Qdrant collection now has {vectors_count} vectors")
    except Exception as exc:
        logger.warning(f"could not verify Qdrant count: {exc}")
    
    driver.close()


if __name__ == "__main__":
    reembed_all()
