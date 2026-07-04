"""Apples-to-apples comparison: old YandexGPT extraction (nlp/pdftest_graph.json)
vs RouterAI models, on the *same* source document and the *same* nodes/edges
schema that nlp/ingestion/neo4j_import.py actually consumes.

Why not reuse llm_ner_extract.py's schema? Because that's a different,
undeployed contract (entities/measurements/relations/findings per
EXTRACTION_SCHEMA.md). The pipeline that actually writes to Neo4j
(NER_pipeline_text_only.py -> neo4j_import.py) uses a simpler ad-hoc
nodes[]/edges[] graph format with no `evidence`/`canonical`/`confidence`
fields. This script uses that same nodes/edges prompt so the comparison
against the old Yandex baseline is fair.

Usage:
    python nlp/benchmark_extraction_vs_yandex.py
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

import requests


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

# Same prompt as NER_pipeline_text_only.py (the schema neo4j_import.py consumes)
SYSTEM_PROMPT = """
Ты — Senior Data Architect в области горно-металлургического R&D.
Твоя задача: извлечь структурированный граф знаний из текста строго по утвержденной онтологии.
Выведи результат СТРОГО в формате JSON без пояснений.

ДОПУСТИМЫЕ ТИПЫ УЗЛОВ (label):
- Material (вещества, металлы, отходы)
- Process (технологии, методы)
- Equipment (оборудование)
- Property (параметр, например "температура", "сухой остаток")
- Measurement (конкретное числовое значение)
- Condition (условие, климат, режим)
- Experiment (опыт)
- Publication (отчет, статья)
- Expert (автор)
- Facility (завод, лаборатория)
- Finding (научный вывод, эффект)
- Topic (тег темы)

ДОПУСТИМЫЕ ТИПЫ СВЯЗЕЙ (type):
uses_material, applies_to, operates_at_condition, has_measurement, measures_property, uses_equipment, produces_output, showed, described_in, authored_by, expert_in, conducted_at, validated_by, contradicts, supports, tagged.

ПРАВИЛА ДЛЯ УЗЛОВ С ПАРАМЕТРАМИ (Measurement и Finding):
1. Если в тексте есть числа (концентрации, размеры, температура), создавай отдельный узел с label="Measurement". В его "properties" укажи: "value" (для точного числа), "min" (от/≥), "max" (до/≤), "unit" (размерность), "operator" (<=, >=, =, range).
2. Обязательно связывай Process/Experiment -> [has_measurement] -> Measurement -> [measures_property] -> Property.
3. ID для узлов Measurement и Finding генерируй как уникальные строки (например, "meas_sulf_200", "finding_yield_85").

Формат ответа:
{
  "nodes": [
    {"id": "обратный осмос", "label": "Process", "properties": {"domain": "экология"}},
    {"id": "шахтная вода", "label": "Material", "properties": {}},
    {"id": "meas_sulf_300", "label": "Measurement", "properties": {"max": 300, "unit": "мг/л", "operator": "<="}},
    {"id": "сульфаты", "label": "Property", "properties": {}}
  ],
  "edges": [
    {"source": "обратный осмос", "target": "шахтная вода", "type": "applies_to"},
    {"source": "обратный осмос", "target": "meas_sulf_300", "type": "has_measurement"},
    {"source": "meas_sulf_300", "target": "сульфаты", "type": "measures_property"}
  ]
}
"""

# Ontology allow-list from EXTRACTION_SCHEMA.md (relation types)
ALLOWED_REL_TYPES = {
    "uses_material", "applies_to", "operates_at_condition", "has_measurement",
    "measures_property", "uses_equipment", "produces_output", "showed",
    "described_in", "authored_by", "expert_in", "conducted_at", "validated_by",
    "contradicts", "supports", "tagged", "has_source",
}
ALLOWED_NODE_LABELS = {
    "Material", "Process", "Equipment", "Property", "Measurement", "Condition",
    "Experiment", "Publication", "Expert", "Facility", "Finding", "Topic",
}

MODELS = [
    "qwen/qwen3-30b-a3b-instruct-2507",   # current cheap/fast winner
]

TEXT = (Path(__file__).parent / "pdftest_RAW_TEXT.txt").read_text(encoding="utf-8")
OLD_GRAPH = json.loads((Path(__file__).parent / "pdftest_graph.json").read_text(encoding="utf-8"))


def chat_completion(model: str, system: str, user: str) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.1,
        "max_tokens": 8000,
    }
    start = time.perf_counter()
    resp = requests.post(f"{BASE_URL}/chat/completions", headers=HEADERS, json=payload, timeout=180)
    elapsed = time.perf_counter() - start
    resp.raise_for_status()
    data = resp.json()
    return {
        "content": data["choices"][0]["message"]["content"],
        "tokens": data.get("usage", {}).get("prompt_tokens", 0) + data.get("usage", {}).get("completion_tokens", 0),
        "elapsed": round(elapsed, 2),
    }


def extract_json(text: str) -> dict[str, Any]:
    if "```" in text:
        text = text.split("```")[1]
        text = text[4:] if text.lower().startswith("json") else text
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return json.loads(match.group(0)) if match else json.loads(text.strip())


def analyze(graph: dict[str, Any]) -> dict[str, Any]:
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    labels = [n.get("label", "") for n in nodes]
    rel_types = [e.get("type", "") for e in edges]
    bad_labels = sorted({l for l in labels if l not in ALLOWED_NODE_LABELS})
    bad_rels = sorted({t for t in rel_types if t not in ALLOWED_REL_TYPES})
    ids = [n.get("id", "").strip().lower().replace("_", " ") for n in nodes]
    dupes = len(ids) - len(set(ids))
    return {
        "n_nodes": len(nodes),
        "n_edges": len(edges),
        "label_counts": {l: labels.count(l) for l in sorted(set(labels))},
        "rel_counts": {t: rel_types.count(t) for t in sorted(set(rel_types))},
        "ontology_violations_labels": bad_labels,
        "ontology_violations_relations": bad_rels,
        "likely_duplicate_nodes": dupes,
    }


def main() -> None:
    print("=" * 70)
    print("OLD (YandexGPT, from pdftest_graph.json)")
    print("=" * 70)
    old_stats = analyze(OLD_GRAPH)
    print(json.dumps(old_stats, ensure_ascii=False, indent=2))

    results = {"yandex_baseline": old_stats}
    for model in MODELS:
        print("\n" + "=" * 70)
        print(model)
        print("=" * 70)
        try:
            r = chat_completion(model, SYSTEM_PROMPT, TEXT)
            try:
                graph = extract_json(r["content"])
            except Exception as parse_exc:
                print(f"PARSE FAILED: {parse_exc}")
                print(f"raw content ({len(r['content'])} chars): {r['content'][:1500]!r}")
                results[model] = {"error": str(parse_exc), "raw": r["content"]}
                continue
            stats = analyze(graph)
            stats["elapsed_seconds"] = r["elapsed"]
            stats["tokens"] = r["tokens"]
            print(json.dumps(stats, ensure_ascii=False, indent=2))
            results[model] = {"stats": stats, "graph": graph}
        except Exception as e:
            print(f"REQUEST FAILED: {e}")
            results[model] = {"error": str(e)}

    out_path = Path(__file__).parent / "extraction_vs_yandex_results.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
