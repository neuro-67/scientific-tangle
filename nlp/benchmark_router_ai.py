"""Benchmark script for Router AI models — fallback provider while Yandex
Cloud is down.

Runs the *actual* production prompts/schemas (nlp/query/prompts.py,
nlp/query/retrieval/synthesis.py, nlp/llm_ner_extract.py) against several
chat models on Router AI's OpenAI-compatible API, so results are directly
comparable to what ML-2 (query parsing/synthesis) and ML-1 (extraction)
will see in prod.

Tasks:
1. Query parsing   — QuerySpec JSON from the 4 golden questions in the ТЗ.
2. Synthesis       — structured answer JSON from a fixed findings context.
3. Extraction      — ontology JSON (entities/measurements/relations/findings)
                     from a real chunk of nlp/sample_text.txt.

Usage:
    pip install requests python-dotenv  # dotenv optional, falls back to manual parse
    python nlp/benchmark_router_ai.py

Requires ROUTERAI_API_KEY in nlp/.env (see nlp/.env.example).
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

from nlp.query.prompts import QUERY_SPEC_SYSTEM, QUERY_SPEC_USER_TEMPLATE
from nlp.query.retrieval.synthesis import SYNTHESIS_SYSTEM_PROMPT
from nlp.llm_ner_extract import EXTRACTION_SYSTEM_PROMPT


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
    raise SystemExit("Set ROUTERAI_API_KEY in nlp/.env (see nlp/.env.example)")

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

OUTPUT_PATH = Path(__file__).parent / "router_ai_benchmark.json"

# Models under evaluation: the 4 requested by the team + 2 cheap/fast
# alternatives spotted in the Router AI catalog (GET /models) that are worth
# comparing against Gemma/Gemini for this workload.
MODELS = [
    "google/gemini-3.1-flash-lite",     # 1M ctx, ~25/152 RUB per 1M tok — requested
    "google/gemma-4-31b-it",            # 262K ctx, ~12/35 RUB per 1M tok — requested
    "google/gemma-4-26b-a4b-it",        # 262K ctx, ~6/33 RUB per 1M tok (MoE, cheapest of the 4) — requested
    "qwen/qwen3.7-plus",                # 1M ctx, ~32/130 RUB per 1M tok — requested
    "deepseek/deepseek-v4-flash",       # 1M ctx, ~9/18 RUB per 1M tok — cheap/fast alternative
    "qwen/qwen3-30b-a3b-instruct-2507", # 131K ctx, MoE, ~5/20 RUB per 1M tok — cheap/fast alternative
]

# The 4 golden questions from the case spec (nlp/query/golden_questions_test.py)
PARSE_TESTS = [
    "методы обессоливания воды: сульфаты/хлориды/Ca/Mg/Na по 200-300 мг/л, сухой остаток <=1000 мг/дм3",
    "оптимальная скорость циркуляции католита в процессе электроэкстракции",
    "извлечение Au, Ag и металлов платиновой группы из руд",
    "закачка воды в горные выработки: методы и оборудование",
]

SYNTHESIS_FINDINGS = [
    {
        "text": "Флотация является основным методом обогащения сульфидных руд золота. Извлечение достигает 85-95%.",
        "source": "Иванов et al., 2023",
        "confidence": 0.92,
    },
    {
        "text": "Цианирование обеспечивает извлечение золота до 98% при правильном контроле pH и концентрации CN-.",
        "source": "Петров et al., 2022",
        "confidence": 0.89,
    },
    {
        "text": "Гравитационное обогащение используется для крупного золота (>0.1 мм) как предварительная стадия.",
        "source": "Сидоров et al., 2024",
        "confidence": 0.78,
    },
]

EXTRACTION_CHUNK = (
    Path(__file__).parent / "sample_text.txt"
).read_text(encoding="utf-8")[2000:5000]  # skip page-1 header noise


def chat_completion(model: str, system: str, user: str, temperature: float = 0.1, max_tokens: int = 2000) -> dict[str, Any]:
    """Call Router AI chat completion API (OpenAI-compatible)."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    start = time.perf_counter()
    response = requests.post(
        f"{BASE_URL}/chat/completions",
        headers=HEADERS,
        json=payload,
        timeout=120,
    )
    elapsed = time.perf_counter() - start
    response.raise_for_status()
    data = response.json()

    return {
        "content": data["choices"][0]["message"]["content"],
        "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
        "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
        "elapsed_seconds": round(elapsed, 2),
    }


def _strip_json(content: str) -> str:
    if "```" in content:
        content = content.split("```")[1]
        content = content[4:] if content.lower().startswith("json") else content
    return content.strip()


def test_parse(model: str) -> dict[str, Any]:
    results = []
    total_time = 0.0
    total_tokens = 0

    for question in PARSE_TESTS:
        user = QUERY_SPEC_USER_TEMPLATE.format(question=question)
        entry: dict[str, Any] = {"question": question}
        try:
            result = chat_completion(model, QUERY_SPEC_SYSTEM, user, temperature=0.1, max_tokens=1000)
            total_time += result["elapsed_seconds"]
            total_tokens += result["prompt_tokens"] + result["completion_tokens"]
            parsed = json.loads(_strip_json(result["content"]))
            entry.update(
                parsed=parsed,
                time=result["elapsed_seconds"],
                tokens=result["prompt_tokens"] + result["completion_tokens"],
                error=None,
            )
        except Exception as e:
            entry.update(parsed=None, time=0, tokens=0, error=str(e))
        results.append(entry)

    n = len(PARSE_TESTS)
    return {
        "model": model,
        "task": "parse",
        "results": results,
        "avg_time": round(total_time / n, 2) if n else 0,
        "total_tokens": total_tokens,
        "ok": sum(1 for r in results if not r["error"]),
        "n": n,
    }


def test_synthesis(model: str) -> dict[str, Any]:
    findings_text = "\n\n".join(
        f"[{i+1}] {f['text']} (Source: {f['source']}, Confidence: {f['confidence']})"
        for i, f in enumerate(SYNTHESIS_FINDINGS)
    )
    user = f"Вопрос: Какие технологии используются для добычи золота?\n\nКонтекст:\n{findings_text}\n\nВерни JSON:"

    try:
        result = chat_completion(model, SYNTHESIS_SYSTEM_PROMPT, user, temperature=0.2, max_tokens=1500)
        parsed = json.loads(_strip_json(result["content"]))
        return {
            "model": model,
            "task": "synthesis",
            "parsed": parsed,
            "time": result["elapsed_seconds"],
            "tokens": result["prompt_tokens"] + result["completion_tokens"],
            "error": None,
        }
    except Exception as e:
        return {"model": model, "task": "synthesis", "parsed": None, "time": 0, "tokens": 0, "error": str(e)}


def test_extraction(model: str) -> dict[str, Any]:
    user = f"Фрагмент текста:\n{EXTRACTION_CHUNK}\n\nВерни JSON:"
    try:
        result = chat_completion(model, EXTRACTION_SYSTEM_PROMPT, user, temperature=0.1, max_tokens=2000)
        parsed = json.loads(_strip_json(result["content"]))
        n_entities = len(parsed.get("entities", []))
        n_relations = len(parsed.get("relations", []))
        return {
            "model": model,
            "task": "extraction",
            "parsed": parsed,
            "n_entities": n_entities,
            "n_relations": n_relations,
            "time": result["elapsed_seconds"],
            "tokens": result["prompt_tokens"] + result["completion_tokens"],
            "error": None,
        }
    except Exception as e:
        return {"model": model, "task": "extraction", "parsed": None, "time": 0, "tokens": 0, "error": str(e)}


def main() -> None:
    print("=" * 70)
    print("Router AI Model Benchmark (parse / synthesis / extraction)")
    print("=" * 70)

    all_results = []
    for model in MODELS:
        print(f"\n--- {model} ---")

        print("  parse...", end=" ", flush=True)
        parse_result = test_parse(model)
        print(f"{parse_result['ok']}/{parse_result['n']} ok, avg {parse_result['avg_time']}s, {parse_result['total_tokens']} tok")

        print("  synthesis...", end=" ", flush=True)
        synth_result = test_synthesis(model)
        print(f"{'ok' if not synth_result['error'] else 'FAIL: ' + synth_result['error']}, {synth_result['time']}s, {synth_result['tokens']} tok")

        print("  extraction...", end=" ", flush=True)
        extract_result = test_extraction(model)
        if extract_result["error"]:
            print(f"FAIL: {extract_result['error']}")
        else:
            print(f"{extract_result['n_entities']} entities, {extract_result['n_relations']} relations, {extract_result['time']}s, {extract_result['tokens']} tok")

        all_results.extend([parse_result, synth_result, extract_result])

    OUTPUT_PATH.write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResults saved to {OUTPUT_PATH}")

    print("\nSUMMARY")
    print(f"{'Model':<32} {'Parse':<8} {'Synth':<8} {'Extract':<10} {'AvgTime(parse)':<16} {'Tokens(all 3 tasks)':<10}")
    print("-" * 95)
    by_model: dict[str, dict[str, Any]] = {}
    for r in all_results:
        by_model.setdefault(r["model"], {})[r["task"]] = r
    for model, tasks in by_model.items():
        p, s, e = tasks.get("parse", {}), tasks.get("synthesis", {}), tasks.get("extraction", {})
        parse_ok = f"{p.get('ok', 0)}/{p.get('n', 0)}"
        synth_ok = "ok" if s and not s.get("error") else "FAIL"
        extract_ok = "ok" if e and not e.get("error") else "FAIL"
        total_tok = p.get("total_tokens", 0) + s.get("tokens", 0) + e.get("tokens", 0)
        print(f"{model.split('/')[-1]:<32} {parse_ok:<8} {synth_ok:<8} {extract_ok:<10} {p.get('avg_time', 0):<16} {total_tok:<10}")


if __name__ == "__main__":
    main()
