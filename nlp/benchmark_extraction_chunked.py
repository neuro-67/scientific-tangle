"""Same comparison as benchmark_extraction_vs_yandex.py, but chunked the way
NER_pipeline_text_only.py actually does it (RecursiveCharacterTextSplitter,
chunk_size=1500, overlap=200) instead of feeding the whole document in one
call. Whole-document-in-one-shot was a worst case; this is the real
production shape.

Usage:
    python nlp/benchmark_extraction_chunked.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from nlp.benchmark_extraction_vs_yandex import (
    SYSTEM_PROMPT,
    analyze,
    extract_json,
)


def recursive_split(text: str, chunk_size: int = 1500, chunk_overlap: int = 200,
                     separators: tuple[str, ...] = ("\n\n", "\n", ".", " ", "")) -> list[str]:
    """Minimal reimplementation of langchain's RecursiveCharacterTextSplitter.

    langchain_text_splitters pulls in langchain_core, whose pydantic v1 shim
    segfaults on Python 3.14 here (same class of issue as GLiNER/onnxruntime
    noted in extraction_gliner.py) -- so this avoids that dependency entirely.
    """
    sep = separators[0]
    rest = separators[1:]
    parts = text.split(sep) if sep else list(text)

    chunks: list[str] = []
    current = ""
    for part in parts:
        piece = part if not current else sep + part
        if len(current) + len(piece) <= chunk_size or not current:
            current += piece
        else:
            if len(current) > chunk_size and rest:
                chunks.extend(recursive_split(current, chunk_size, chunk_overlap, rest))
            else:
                chunks.append(current)
            # start next chunk with overlap from the tail of the previous one
            overlap_text = current[-chunk_overlap:] if chunk_overlap else ""
            current = overlap_text + piece
    if current:
        if len(current) > chunk_size and rest:
            chunks.extend(recursive_split(current, chunk_size, chunk_overlap, rest))
        else:
            chunks.append(current)
    return chunks


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key, value)


_load_env_file(Path(__file__).parent / ".env")

API_KEY = os.environ.get("ROUTERAI_API_KEY", "")
BASE_URL = os.environ.get("ROUTERAI_BASE_URL", "https://routerai.ru/api/v1")
if not API_KEY:
    raise SystemExit("Set ROUTERAI_API_KEY in nlp/.env")

HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

MODEL = "qwen/qwen3-30b-a3b-instruct-2507"

TEXT = (Path(__file__).parent / "pdftest_RAW_TEXT.txt").read_text(encoding="utf-8")
OLD_GRAPH = json.loads((Path(__file__).parent / "pdftest_graph.json").read_text(encoding="utf-8"))

CHUNKS = recursive_split(TEXT, chunk_size=1500, chunk_overlap=200)


def chat_completion(model: str, system: str, user: str) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.1,
        "max_tokens": 2000,  # same budget as NER_pipeline_text_only.py per-chunk
    }
    start = time.perf_counter()
    resp = requests.post(f"{BASE_URL}/chat/completions", headers=HEADERS, json=payload, timeout=90)
    elapsed = time.perf_counter() - start
    resp.raise_for_status()
    data = resp.json()
    return {
        "content": data["choices"][0]["message"]["content"],
        "tokens": data.get("usage", {}).get("prompt_tokens", 0) + data.get("usage", {}).get("completion_tokens", 0),
        "elapsed": round(elapsed, 2),
    }


def main() -> None:
    print(f"Document split into {len(CHUNKS)} chunks (chunk_size=1500, overlap=200)")
    for i, c in enumerate(CHUNKS):
        print(f"  chunk {i+1}: {len(c)} chars")

    print("\n" + "=" * 70)
    print("OLD (YandexGPT, from pdftest_graph.json) -- also chunked+merged originally")
    print("=" * 70)
    print(json.dumps(analyze(OLD_GRAPH), ensure_ascii=False, indent=2))

    all_nodes: list[dict] = []
    all_edges: list[dict] = []
    total_time = 0.0
    total_tokens = 0
    per_chunk = []

    for i, chunk in enumerate(CHUNKS):
        print(f"\n--- chunk {i+1}/{len(CHUNKS)} ---")
        try:
            r = chat_completion(MODEL, SYSTEM_PROMPT, chunk)
            graph = extract_json(r["content"])
            n_nodes, n_edges = len(graph.get("nodes", [])), len(graph.get("edges", []))
            print(f"  ok: {n_nodes} nodes, {n_edges} edges, {r['elapsed']}s, {r['tokens']} tok")
            all_nodes.extend(graph.get("nodes", []))
            all_edges.extend(graph.get("edges", []))
            total_time += r["elapsed"]
            total_tokens += r["tokens"]
            per_chunk.append({"chunk": i, "n_nodes": n_nodes, "n_edges": n_edges, "elapsed": r["elapsed"], "tokens": r["tokens"], "error": None})
        except Exception as e:
            print(f"  FAILED: {e}")
            per_chunk.append({"chunk": i, "error": str(e)})

    merged = {"nodes": all_nodes, "edges": all_edges}
    stats = analyze(merged)
    stats["total_elapsed_seconds"] = round(total_time, 2)
    stats["total_tokens"] = total_tokens
    stats["n_chunks"] = len(CHUNKS)

    print("\n" + "=" * 70)
    print(f"{MODEL} -- merged across {len(CHUNKS)} chunks")
    print("=" * 70)
    print(json.dumps(stats, ensure_ascii=False, indent=2))

    out_path = Path(__file__).parent / "extraction_chunked_results.json"
    out_path.write_text(
        json.dumps({"per_chunk": per_chunk, "merged_stats": stats, "merged_graph": merged}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
