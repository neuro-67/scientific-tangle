"""Test whether RouterAI's response_format/structured_outputs (server-side
grammar-constrained decoding, same family as Outlines/xgrammar -- just
hosted rather than run locally) fixes the two recurring problems seen in
nlp/run_corpus_test.py:
  1. Truncated/malformed JSON on dense chunks
  2. Invented out-of-ontology labels/relations (uses_process, Document, ...)

Re-runs the exact chunks that failed earlier (Fedoseev doc, chunks 2/4/9 of
11) with a JSON Schema that enum-constrains "label" and "type" fields to the
allowed ontology values, and compares against the unconstrained baseline.

Usage:
    python nlp/test_structured_output.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from nlp.benchmark_extraction_chunked import recursive_split
from nlp.run_corpus_test import SYSTEM_PROMPT, extract_pdf_text, extract_json


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key, value)


_load_env_file(Path(__file__).parent.parent / ".env")

API_KEY = os.environ.get("ROUTERAI_API_KEY", "")
BASE_URL = os.environ.get("ROUTERAI_BASE_URL", "https://routerai.ru/api/v1")
if not API_KEY:
    raise SystemExit("Set ROUTERAI_API_KEY in .env (repo root)")

HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
MODEL = "qwen/qwen3-30b-a3b-instruct-2507"

ONTOLOGY_LABELS = ["Material", "Process", "Equipment", "Property", "Measurement", "Condition",
                   "Experiment", "Publication", "Expert", "Facility", "Finding", "Topic", "Source"]
ONTOLOGY_RELATIONS = ["uses_material", "applies_to", "operates_at_condition", "has_measurement",
                      "measures_property", "uses_equipment", "produces_output", "showed",
                      "described_in", "authored_by", "expert_in", "conducted_at", "validated_by",
                      "contradicts", "supports", "tagged", "has_source"]

JSON_SCHEMA = {
    "name": "knowledge_graph",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "nodes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "label": {"type": "string", "enum": ONTOLOGY_LABELS},
                        "properties": {"type": "object", "additionalProperties": True},
                    },
                    "required": ["id", "label", "properties"],
                    "additionalProperties": False,
                },
            },
            "edges": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string"},
                        "target": {"type": "string"},
                        "type": {"type": "string", "enum": ONTOLOGY_RELATIONS},
                    },
                    "required": ["source", "target", "type"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["nodes", "edges"],
        "additionalProperties": False,
    },
}


def call(system: str, user: str, use_schema: bool, max_tokens: int = 3000) -> dict[str, Any]:
    payload = {
        "model": MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }
    if use_schema:
        payload["response_format"] = {"type": "json_schema", "json_schema": JSON_SCHEMA}

    start = time.perf_counter()
    resp = requests.post(f"{BASE_URL}/chat/completions", headers=HEADERS, json=payload, timeout=120)
    elapsed = time.perf_counter() - start
    ok_http = resp.status_code == 200
    body = None
    error = None
    if ok_http:
        data = resp.json()
        body = data["choices"][0]["message"]["content"]
    else:
        error = f"HTTP {resp.status_code}: {resp.text[:500]}"
    return {"ok_http": ok_http, "content": body, "error": error, "elapsed": round(elapsed, 2)}


def main() -> None:
    pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if not pdf_path or not pdf_path.exists():
        print("Usage: python nlp/test_structured_output.py <path-to-fedoseev-pdf>")
        sys.exit(1)

    text = extract_pdf_text(pdf_path)
    chunks = recursive_split(text, chunk_size=1500, chunk_overlap=200)
    print(f"{len(chunks)} chunks total")

    # chunks 2, 4, 9 (1-indexed) failed with truncation in the earlier run
    target_indices = [1, 3, 8]
    target_indices = [i for i in target_indices if i < len(chunks)]

    for idx in target_indices:
        chunk = chunks[idx]
        print(f"\n{'='*70}\nchunk {idx+1}/{len(chunks)} ({len(chunk)} chars)\n{'='*70}")

        print("-- WITHOUT response_format (baseline) --")
        r1 = call(SYSTEM_PROMPT, chunk, use_schema=False)
        if not r1["ok_http"]:
            print(f"HTTP FAILED: {r1['error']}")
        else:
            try:
                g1 = extract_json(r1["content"])
                bad_labels = sorted({n.get("label") for n in g1.get("nodes", [])} - set(ONTOLOGY_LABELS))
                bad_rels = sorted({e.get("type") for e in g1.get("edges", [])} - set(ONTOLOGY_RELATIONS))
                print(f"ok: {len(g1.get('nodes',[]))} nodes, {len(g1.get('edges',[]))} edges, {r1['elapsed']}s, bad_labels={bad_labels}, bad_rels={bad_rels}")
            except Exception as e:
                print(f"PARSE FAILED: {e} (content length {len(r1['content'] or '')})")

        print("-- WITH response_format (JSON schema, enum-constrained) --")
        r2 = call(SYSTEM_PROMPT, chunk, use_schema=True)
        if not r2["ok_http"]:
            print(f"HTTP FAILED: {r2['error']}")
        else:
            try:
                g2 = extract_json(r2["content"])
                bad_labels = sorted({n.get("label") for n in g2.get("nodes", [])} - set(ONTOLOGY_LABELS))
                bad_rels = sorted({e.get("type") for e in g2.get("edges", [])} - set(ONTOLOGY_RELATIONS))
                print(f"ok: {len(g2.get('nodes',[]))} nodes, {len(g2.get('edges',[]))} edges, {r2['elapsed']}s, bad_labels={bad_labels}, bad_rels={bad_rels}")
            except Exception as e:
                print(f"PARSE FAILED: {e} (content length {len(r2['content'] or '')})")


if __name__ == "__main__":
    main()
