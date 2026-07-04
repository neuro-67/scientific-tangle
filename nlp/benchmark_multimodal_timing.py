"""Time comparison: text-only ingestion (NER_pipeline_text_only.py) vs
text+vision-augmented ingestion (NER_pipeline_multimodal_aug.py) for the
same document (nlp/pdftest.pdf, 12 pages), via RouterAI.

Same model (google/gemini-3.1-flash-lite) is used for both the vision
description step and the text extraction step, so the only variable is
"do we pay for a per-page vision call or not".

Usage:
    pip install pymupdf
    python nlp/benchmark_multimodal_timing.py
"""

from __future__ import annotations

import base64
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import pymupdf
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from nlp.benchmark_extraction_chunked import recursive_split
from nlp.benchmark_extraction_vs_yandex import SYSTEM_PROMPT, analyze, extract_json


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
MODEL = "google/gemini-3.1-flash-lite"  # same model for vision + text, per the aug script's split of roles

VISION_PROMPT = (
    "Ты эксперт-металлург. Внимательно изучи эту страницу научно-технического отчёта/презентации. "
    "На ней могут быть результаты математического моделирования (CFD), цветные тепловые карты, "
    "схемы печей, графики скоростей/давлений/температур. Опиши максимально подробно, что видишь: "
    "какое оборудование, какие процессы, какие числовые значения на шкалах (в мм, К, м/с). "
    "Если на странице нет картинок/схем/цветовых карт, ответь 'ПУСТО'."
)

PDF_PATH = Path(__file__).parent / "pdftest.pdf"


def chat_text(model: str, system: str, user: str, max_tokens: int = 2000) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }
    start = time.perf_counter()
    resp = requests.post(f"{BASE_URL}/chat/completions", headers=HEADERS, json=payload, timeout=90)
    elapsed = time.perf_counter() - start
    resp.raise_for_status()
    data = resp.json()
    return {"content": data["choices"][0]["message"]["content"], "elapsed": round(elapsed, 2)}


def chat_vision(model: str, prompt: str, image_bytes: bytes) -> dict[str, Any]:
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    payload = {
        "model": model,
        "temperature": 0.1,
        "max_tokens": 800,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}},
                ],
            }
        ],
    }
    start = time.perf_counter()
    resp = requests.post(f"{BASE_URL}/chat/completions", headers=HEADERS, json=payload, timeout=90)
    elapsed = time.perf_counter() - start
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"].get("content") or ""
    return {"content": content.strip(), "elapsed": round(elapsed, 2)}


def run_extraction(text: str) -> dict[str, Any]:
    """Chunk text (chunk_size=1500/overlap=200, matching prod) and extract per chunk."""
    chunks = recursive_split(text, chunk_size=1500, chunk_overlap=200)
    all_nodes, all_edges = [], []
    total_time = 0.0
    ok, failed = 0, 0
    for chunk in chunks:
        r = chat_text(MODEL, SYSTEM_PROMPT, chunk)
        total_time += r["elapsed"]
        try:
            graph = extract_json(r["content"])
            all_nodes.extend(graph.get("nodes", []))
            all_edges.extend(graph.get("edges", []))
            ok += 1
        except Exception:
            failed += 1
    return {
        "n_chunks": len(chunks),
        "ok_chunks": ok,
        "failed_chunks": failed,
        "extraction_seconds": round(total_time, 2),
        "graph": {"nodes": all_nodes, "edges": all_edges},
    }


def main() -> None:
    doc = pymupdf.open(PDF_PATH)
    pages_native_text = []
    for page in doc:
        pages_native_text.append(page.get_text("text").strip())

    # ---------- Variant A: text-only (no images) ----------
    print("=" * 70)
    print("VARIANT A: text-only (no images) -- NER_pipeline_text_only.py shape")
    print("=" * 70)
    full_text_only = "\n\n".join(
        f"--- СТРАНИЦА {i+1} ---\n{t}" for i, t in enumerate(pages_native_text)
    )
    t0 = time.perf_counter()
    extract_a = run_extraction(full_text_only)
    wall_a = time.perf_counter() - t0
    stats_a = analyze(extract_a["graph"])
    print(f"parse step: instant (PyMuPDF, no LLM call)")
    print(f"extraction: {extract_a['n_chunks']} chunks, {extract_a['ok_chunks']} ok, {extract_a['failed_chunks']} failed, {extract_a['extraction_seconds']}s")
    print(f"TOTAL WALL TIME: {round(wall_a, 2)}s")
    print(json.dumps(stats_a, ensure_ascii=False, indent=2))

    # ---------- Variant B: text + per-page vision descriptions ----------
    print("\n" + "=" * 70)
    print("VARIANT B: text + images -- NER_pipeline_multimodal_aug.py shape")
    print("=" * 70)
    t0 = time.perf_counter()
    vision_time = 0.0
    pages_augmented = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=150)
        image_bytes = pix.tobytes("jpeg")
        r = chat_vision(MODEL, VISION_PROMPT, image_bytes)
        vision_time += r["elapsed"]
        desc = "" if r["content"].upper().startswith("ПУСТО") else r["content"]
        combined = pages_native_text[i]
        if desc:
            combined += f"\n[ОПИСАНИЕ ГРАФИКОВ/СХЕМ]: {desc}"
        pages_augmented.append(combined)
        print(f"  page {i+1}/12: vision call {r['elapsed']}s, {'visual content found' if desc else 'empty/no visuals'}")

    full_text_aug = "\n\n".join(f"--- СТРАНИЦА {i+1} ---\n{t}" for i, t in enumerate(pages_augmented))
    extract_b = run_extraction(full_text_aug)
    wall_b = time.perf_counter() - t0
    stats_b = analyze(extract_b["graph"])
    print(f"\nvision step: 12 pages, {round(vision_time, 2)}s total")
    print(f"extraction: {extract_b['n_chunks']} chunks, {extract_b['ok_chunks']} ok, {extract_b['failed_chunks']} failed, {extract_b['extraction_seconds']}s")
    print(f"TOTAL WALL TIME: {round(wall_b, 2)}s")
    print(json.dumps(stats_b, ensure_ascii=False, indent=2))

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Variant A (no images): {round(wall_a, 2)}s total, {stats_a['n_nodes']} nodes, {stats_a['n_edges']} edges")
    print(f"Variant B (with images): {round(wall_b, 2)}s total ({round(vision_time,2)}s vision + {extract_b['extraction_seconds']}s extraction), {stats_b['n_nodes']} nodes, {stats_b['n_edges']} edges")
    print(f"Overhead from images: +{round(wall_b - wall_a, 2)}s ({round((wall_b/wall_a - 1) * 100)}% slower)")

    out = {"variant_a": {"wall_seconds": wall_a, "stats": stats_a}, "variant_b": {"wall_seconds": wall_b, "vision_seconds": vision_time, "stats": stats_b}}
    Path(__file__).with_name("multimodal_timing_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
