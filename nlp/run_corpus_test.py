"""Run the ingestion pipeline (parse -> chunk -> extract) on a handful of real
documents from the case corpus, using RouterAI (qwen3-30b-a3b, our chosen
ingestion model) instead of the down YandexGPT endpoint.

Adds Source/has_source (missing from the old SYSTEM_PROMPT vs docs/ONTOLOGY.md)
plus explicit confidence on Finding and validated_by, since the team wants
provenance/freshness/confidence/expert features surfaced, not just entities.

Usage:
    python nlp/run_corpus_test.py <pdf1> [pdf2 ...]
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import pymupdf
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from nlp.benchmark_extraction_chunked import recursive_split

TERM_ALIASES: dict[str, str] = json.loads(
    (Path(__file__).parent / "term_aliases.json").read_text(encoding="utf-8")
)
TERM_ALIASES.pop("_comment", None)
TERM_ALIASES = {k.lower(): v for k, v in TERM_ALIASES.items()}


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

ONTOLOGY_LABELS = ["Material", "Process", "Equipment", "Property", "Measurement", "Condition",
                   "Experiment", "Publication", "Expert", "Facility", "Finding", "Topic", "Source"]
ONTOLOGY_RELATIONS = ["uses_material", "applies_to", "operates_at_condition", "has_measurement",
                      "measures_property", "uses_equipment", "produces_output", "showed",
                      "described_in", "authored_by", "expert_in", "conducted_at", "validated_by",
                      "contradicts", "supports", "tagged", "has_source"]

# Server-side grammar-constrained decoding (RouterAI's response_format/structured_outputs,
# same family of technique as Outlines/xgrammar): enum-constrains label/type so the model
# cannot emit an out-of-ontology value (confirmed empirically: 0 violations when generation
# completes within max_tokens -- see nlp/test_structured_output.py).
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

# SYSTEM_PROMPT extended with Source/has_source (present in docs/ONTOLOGY.md,
# missing from the original NER_pipeline_text_only.py prompt) + explicit
# confidence/validated_by guidance, per the team's request to surface
# provenance/freshness/confidence/experts.
SYSTEM_PROMPT = """
Ты — Senior Data Architect в области горно-металлургического R&D.
Твоя задача: извлечь структурированный граф знаний из текста строго по утвержденной онтологии.
Выведи результат СТРОГО в формате JSON без пояснений.

КРИТИЧЕСКИ ВАЖНО (ошибки в числах недопустимы):
Извлекай числовые значения ТОЛЬКО если конкретное число явно написано в тексте.
Если текст говорит, что параметр "измерялся"/"моделировался"/"был получен", но
САМО ЧИСЛО в тексте не указано — НЕ создавай узел Measurement с придуманным
значением. В этом случае создай узел Property/Finding без числа, либо вообще
не создавай узел. Никогда не додумывай правдоподобные на вид цифры.

ДОПУСТИМЫЕ ТИПЫ УЗЛОВ (label):
- Material (вещества, металлы, отходы)
- Process (технологии, методы)
- Equipment (оборудование)
- Property (параметр, например "температура", "сухой остаток")
- Measurement (конкретное числовое значение)
- Condition (условие, климат, режим)
- Experiment (опыт)
- Publication (отчет, статья, доклад)
- Expert (автор, докладчик)
- Facility (завод, лаборатория, институт)
- Finding (научный вывод, эффект)
- Topic (тег темы)
- Source (провенанс: конкретная страница/фрагмент документа, откуда взят факт)

ДОПУСТИМЫЕ ТИПЫ СВЯЗЕЙ (type):
uses_material, applies_to, operates_at_condition, has_measurement, measures_property, uses_equipment,
produces_output, showed, described_in, authored_by, expert_in, conducted_at, validated_by,
contradicts, supports, tagged, has_source.

ПРАВИЛА ДЛЯ УЗЛОВ С ПАРАМЕТРАМИ (Measurement и Finding):
1. Если в тексте есть числа (концентрации, размеры, температура), создавай отдельный узел с label="Measurement". В его "properties" укажи: "value" (для точного числа), "min" (от/≥), "max" (до/≤), "unit" (размерность), "operator" (<=, >=, =, range).
2. Обязательно связывай Process/Experiment -> [has_measurement] -> Measurement -> [measures_property] -> Property.
3. Для каждого Finding обязательно указывай "confidence" в properties: "high" (авторский вывод/измерение из этого документа), "medium" (со ссылкой на другой источник), "low" (предположение/гипотеза).
4. ID для узлов Measurement и Finding генерируй как уникальные строки (например, "meas_sulf_200", "finding_yield_85").

ПРАВИЛА ДЛЯ ПРОВЕНАНСА (Source):
5. Текст размечен маркерами "--- СТРАНИЦА N ---". Для каждого значимого факта (Finding, Measurement, ключевая связь) создавай узел Source с properties {"span": "p.N"}, где N — номер страницы из ближайшего маркера, и связывай факт -> [has_source] -> Source.
6. Если в тексте указан автор/докладчик — создавай Expert и связывай Publication -> [authored_by] -> Expert, а вывод -> [validated_by] -> Expert, если именно этот автор сделал измерение/вывод.

ПРАВИЛА КАНОНИЗАЦИИ (важно, иначе граф засоряется дублями одной сущности):
7. У каждого человека — РОВНО ОДИН узел Expert. Используй только полное имя кириллицей в естественном порядке ("Иванов Иван Иванович"), НИКОГДА не создавай второй узел для транслитерации ("ivanov_ivan_ivanovich"), email или инициалов той же персоны — если встречаешь такой вариант, это тот же узел, что и полное имя.
8. Email, ORCID, должность добавляй как properties существующего узла Expert (например {"email": "..."}), а не как отдельный узел.
9. Для Publication указывай "geography" в properties: "RU", если это отечественный источник/автор/предприятие, "foreign" — если зарубежный.

Формат ответа:
{
  "nodes": [
    {"id": "обратный осмос", "label": "Process", "properties": {"domain": "экология"}},
    {"id": "meas_sulf_300", "label": "Measurement", "properties": {"max": 300, "unit": "мг/л", "operator": "<="}},
    {"id": "src_p12", "label": "Source", "properties": {"span": "p.12"}}
  ],
  "edges": [
    {"source": "обратный осмос", "target": "meas_sulf_300", "type": "has_measurement"},
    {"source": "meas_sulf_300", "target": "src_p12", "type": "has_source"}
  ]
}
"""


def chat_completion(model: str, system: str, user: str, max_tokens: int = 6000) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.1,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_schema", "json_schema": JSON_SCHEMA},
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


def extract_pdf_text(pdf_path: Path) -> str:
    doc = pymupdf.open(pdf_path)
    parts = []
    for i, page in enumerate(doc):
        text = page.get_text("text").strip()
        if text:
            parts.append(f"--- СТРАНИЦА {i+1} ---\n{text}")
    doc.close()
    return "\n\n".join(parts)


def apply_term_aliases(nodes: list[dict], edges: list[dict]) -> tuple[list[dict], list[dict]]:
    """Normalize step (docs/NLP_PIPELINE.md [5]): rename node ids that match a
    known synonym/alias (RU/EN, e.g. "ПВП"/"fluidized bed furnace"/"печь
    взвешенной плавки") to one canonical form, via nlp/term_aliases.json, so
    the same real-world concept doesn't end up as separate graph nodes just
    because it was mentioned in a different language or spelling. Runs before
    merge_duplicate_nodes(), which then folds the resulting same-id duplicates
    together.
    """
    id_map: dict[str, str] = {}
    renamed_nodes = []
    for node in nodes:
        raw_id = node.get("id", "")
        canonical = TERM_ALIASES.get(raw_id.strip().lower())
        new_id = canonical if canonical else raw_id
        id_map[raw_id] = new_id
        renamed_nodes.append({**node, "id": new_id})

    renamed_edges = [
        {**edge, "source": id_map.get(edge.get("source", ""), edge.get("source", "")),
         "target": id_map.get(edge.get("target", ""), edge.get("target", ""))}
        for edge in edges
    ]
    return renamed_nodes, renamed_edges


def merge_duplicate_nodes(nodes: list[dict], edges: list[dict]) -> tuple[list[dict], list[dict]]:
    """Merge nodes whose id normalizes to the same string (case/whitespace only --
    catches simple duplicates from independent chunk extractions; transliteration
    duplicates are addressed at the prompt level, see SYSTEM_PROMPT rules 7-8).
    """
    canonical_id: dict[str, str] = {}
    merged: dict[str, dict] = {}
    for node in nodes:
        raw_id = node.get("id", "")
        key = raw_id.strip().lower()
        if key not in canonical_id:
            canonical_id[key] = raw_id
            merged[raw_id] = {"id": raw_id, "label": node.get("label"), "properties": dict(node.get("properties", {}))}
        else:
            target = merged[canonical_id[key]]
            target["properties"].update(node.get("properties", {}))

    id_map = {raw_id: canonical_id[raw_id.strip().lower()] for raw_id in
              {n.get("id", "") for n in nodes}}

    remapped_edges = []
    seen = set()
    for edge in edges:
        source = id_map.get(edge.get("source", ""), edge.get("source", ""))
        target = id_map.get(edge.get("target", ""), edge.get("target", ""))
        etype = edge.get("type", "")
        key = (source, target, etype)
        if key in seen:
            continue
        seen.add(key)
        remapped_edges.append({"source": source, "target": target, "type": etype})

    return list(merged.values()), remapped_edges


def _number_variants(value: float) -> list[str]:
    """Plausible literal spellings of a number as it might appear in RU text."""
    variants = set()
    for v in (value, round(value, 1), round(value, 2), int(value) if float(value).is_integer() else None):
        if v is None:
            continue
        variants.add(str(v))
        variants.add(str(v).replace(".", ","))
        if isinstance(v, float) and v == int(v):
            variants.add(str(int(v)))
    return [v for v in variants if v]


def verify_measurements(nodes: list[dict], source_text: str) -> list[dict]:
    """Mechanically check each Measurement's value/min/max against the raw
    source text, since prompting alone does not reliably prevent the model
    from substituting a plausible-looking number (e.g. 101325 Pa = standard
    atmospheric pressure) when the text describes a measurement without
    actually stating its value -- confirmed empirically on real corpus data.
    Unverified measurements are flagged, not silently dropped, so a human can
    review them (mirrors the confidence/provenance model, not a delete).
    """
    for node in nodes:
        if node.get("label") != "Measurement":
            continue
        props = node.get("properties", {})
        numbers = [props[k] for k in ("value", "min", "max") if isinstance(props.get(k), (int, float))]
        if not numbers:
            continue
        found = any(
            variant in source_text
            for n in numbers
            for variant in _number_variants(n)
        )
        props["verified"] = found
    return nodes


def process_chunk(chunk: str) -> dict[str, Any]:
    try:
        r = chat_completion(MODEL, SYSTEM_PROMPT, chunk)
        graph = extract_json(r["content"])
        return {"ok": True, "nodes": graph.get("nodes", []), "edges": graph.get("edges", []),
                "elapsed": r["elapsed"], "tokens": r["tokens"]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def process_document(pdf_path: Path, out_dir: Path) -> dict[str, Any]:
    print(f"\n=== {pdf_path.name} ===")
    text = extract_pdf_text(pdf_path)
    print(f"  extracted {len(text)} chars of native text")
    chunks = recursive_split(text, chunk_size=1500, chunk_overlap=200)
    print(f"  split into {len(chunks)} chunks")

    all_nodes, all_edges = [], []
    ok_count, fail_count = 0, 0
    total_time, total_tokens = 0.0, 0

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(process_chunk, c): i for i, c in enumerate(chunks)}
        for fut in as_completed(futures):
            i = futures[fut]
            result = fut.result()
            if result["ok"]:
                all_nodes.extend(result["nodes"])
                all_edges.extend(result["edges"])
                total_time += result["elapsed"]
                total_tokens += result["tokens"]
                ok_count += 1
                print(f"  chunk {i+1}/{len(chunks)}: ok, {len(result['nodes'])} nodes, {len(result['edges'])} edges, {result['elapsed']}s")
            else:
                fail_count += 1
                print(f"  chunk {i+1}/{len(chunks)}: FAILED - {result['error']}")

    all_nodes, all_edges = apply_term_aliases(all_nodes, all_edges)
    all_nodes, all_edges = merge_duplicate_nodes(all_nodes, all_edges)
    all_nodes = verify_measurements(all_nodes, text)

    graph = {"document": pdf_path.name, "nodes": all_nodes, "edges": all_edges}
    out_path = out_dir / f"{pdf_path.stem}_graph.json"
    out_path.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")

    labels = [n.get("label", "") for n in all_nodes]
    rels = [e.get("type", "") for e in all_edges]
    unverified = [n for n in all_nodes if n.get("label") == "Measurement" and n.get("properties", {}).get("verified") is False]
    stats = {
        "document": pdf_path.name,
        "chars": len(text),
        "n_chunks": len(chunks),
        "ok_chunks": ok_count,
        "failed_chunks": fail_count,
        "n_nodes": len(all_nodes),
        "n_edges": len(all_edges),
        "label_counts": {l: labels.count(l) for l in sorted(set(labels))},
        "rel_counts": {t: rels.count(t) for t in sorted(set(rels))},
        "unverified_measurements": [n["id"] for n in unverified],
        "total_llm_seconds": round(total_time, 2),
        "total_tokens": total_tokens,
        "output_file": str(out_path),
    }
    if unverified:
        print(f"  WARNING: {len(unverified)} Measurement(s) failed value verification against source text: {[n['id'] for n in unverified]}")
    print(f"  -> {len(all_nodes)} nodes, {len(all_edges)} edges saved to {out_path}")
    return stats


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python nlp/run_corpus_test.py <pdf1> [pdf2 ...]")
        sys.exit(1)

    out_dir = Path(__file__).parent / "corpus_test_results"
    out_dir.mkdir(exist_ok=True)

    all_stats = []
    t0 = time.perf_counter()
    for arg in sys.argv[1:]:
        stats = process_document(Path(arg), out_dir)
        all_stats.append(stats)
    total_wall = time.perf_counter() - t0

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps({"total_wall_seconds": total_wall, "documents": all_stats}, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for s in all_stats:
        print(f"{s['document']}: {s['n_nodes']} nodes, {s['n_edges']} edges, {s['ok_chunks']}/{s['n_chunks']} chunks ok, {s['total_llm_seconds']}s LLM time")
    print(f"\nTotal wall time: {round(total_wall, 2)}s")
    print(f"Summary saved to {summary_path}")


if __name__ == "__main__":
    main()
