"""Cross-lingual / semantic node deduplication for the knowledge graph.

The extraction LLM emits the same real-world concept as separate nodes when it
appears in different languages or spellings -- "electrowinning" vs
"электроэкстракция", "flash smelting furnace" vs "печь взвешенной плавки". The
static term_aliases.json only covers hand-listed pairs and merge_duplicate_nodes
only folds case/whitespace variants, so cross-lingual duplicates survive and
fragment the graph (and split an entity's evidence across two nodes).

This runs AFTER extraction, when the DB is formed (the stage the case owner
asked about): it embeds the distinct node names per label, finds candidate
near-duplicate pairs by cosine similarity, and -- because bge-m3 cross-lingual
similarity alone is too weakly separated to merge safely (synonyms ~0.58 vs
distinct metals ~0.52 on this corpus) -- confirms each candidate with a single
batched LLM call before merging. Embeddings are the cheap pre-filter; the LLM
is the accurate arbiter that actually knows electrowinning == электроэкстракция.

Default is a DRY RUN (embeddings only, no chat tokens): it reports candidate
pairs. Pass --apply to run the LLM confirmation and merge. Merge moves every
relationship off the duplicate onto the canonical node, then deletes the
duplicate, so no edges are lost.

Usage:
    python -m nlp.ingestion.semantic_dedup                 # dry run, report
    python -m nlp.ingestion.semantic_dedup --apply         # confirm + merge
    python -m nlp.ingestion.semantic_dedup --labels Material Process --threshold 0.6
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nlp.ingestion.neo4j_import import _get_neo4j_driver

# Labels worth deduping: real-world concepts prone to RU/EN duplication.
# Instance-like labels (Measurement, Source, Finding, Publication, Expert) are
# excluded -- they're specific occurrences, not reusable concepts, and merging
# them by name similarity would be wrong.
_DEDUP_LABELS = ["Material", "Process", "Equipment", "Property", "Topic", "Condition"]

# bge-m3 cross-lingual cosine on this corpus is compressed (synonyms ~0.59,
# distinct metals ~0.52), so the candidate cutoff is deliberately LOW for high
# recall -- the LLM confirmation step below removes the false positives
# (медь/никель etc). Precision comes from the LLM, not the threshold.
_EMBED_MODEL = "baai/bge-m3"
_DEFAULT_THRESHOLD = 0.52


def _load_env() -> tuple[str, str]:
    for path in (Path(__file__).parent.parent / ".env", Path(__file__).parent.parent.parent / ".env"):
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k, v.strip())
    key = os.environ.get("ROUTERAI_API_KEY", "")
    base = os.environ.get("ROUTERAI_BASE_URL", "https://routerai.ru/api/v1")
    if not key:
        raise SystemExit("Set ROUTERAI_API_KEY (nlp/.env or root .env)")
    return key, base


def _embed_batch(names: list[str], key: str, base: str) -> dict[str, list[float]]:
    """Embed names via RouterAI bge-m3 (multilingual). Cheap: names are short."""
    out: dict[str, list[float]] = {}
    for i in range(0, len(names), 64):
        chunk = names[i : i + 64]
        resp = requests.post(
            f"{base}/embeddings",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": _EMBED_MODEL, "input": chunk},
            timeout=60,
        )
        resp.raise_for_status()
        for name, item in zip(chunk, resp.json()["data"]):
            out[name] = item["embedding"]
    return out


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def _distinct_names(driver, label: str) -> list[str]:
    with driver.session() as session:
        rows = session.run(
            f"MATCH (n:{label}) WHERE coalesce(n.stub, false) = false RETURN n.id AS id"
        )
        return [r["id"] for r in rows if r["id"]]


def _candidate_pairs(names: list[str], key: str, base: str, threshold: float) -> list[tuple[str, str, float]]:
    if len(names) < 2:
        return []
    vecs = _embed_batch(names, key, base)
    pairs: list[tuple[str, str, float]] = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            if a.strip().lower() == b.strip().lower():
                continue  # already handled by exact/case merge
            sim = _cosine(vecs[a], vecs[b])
            if sim >= threshold:
                pairs.append((a, b, round(sim, 3)))
    pairs.sort(key=lambda p: p[2], reverse=True)
    return pairs


def _confirm_with_llm(pairs: list[tuple[str, str, float]], label: str, key: str, base: str) -> dict[str, str]:
    """Ask the LLM which candidate pairs are truly the same concept, and which
    name is the canonical (RU) form. Returns {duplicate_id: canonical_id}."""
    if not pairs:
        return {}
    listing = "\n".join(f'{i}. "{a}"  <>  "{b}"' for i, (a, b, _) in enumerate(pairs))
    system = (
        "Ты — эксперт по горно-металлургической терминологии. Тебе дают пары "
        "названий сущностей типа '" + label + "' из графа знаний. Некоторые пары — "
        "это ОДИН И ТОТ ЖЕ концепт на разных языках или в разном написании "
        "(например 'electrowinning' и 'электроэкстракция'), а некоторые — РАЗНЫЕ "
        "концепты (например 'медь' и 'никель'). Для каждой пары реши: одно и то же "
        "или нет. Если одно и то же — выбери каноническую форму (предпочитай полное "
        "русское название). Верни СТРОГО JSON-массив объектов "
        '{"i": индекс_пары, "same": true/false, "canonical": "каноническое имя"} '
        "без пояснений."
    )
    payload = {
        "model": os.environ.get("ROUTERAI_MODEL", "google/gemini-3.1-flash-lite"),
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": listing}],
        "temperature": 0.0,
        "max_tokens": 4000,
    }
    resp = requests.post(
        f"{base}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"]
    start, end = text.find("["), text.rfind("]")
    decisions = json.loads(text[start : end + 1]) if start >= 0 else []

    mapping: dict[str, str] = {}
    for d in decisions:
        if not d.get("same"):
            continue
        idx = d.get("i")
        if idx is None or idx >= len(pairs):
            continue
        a, b, _ = pairs[idx]
        canonical = d.get("canonical") or a
        duplicate = b if canonical.strip() == a.strip() else a
        if duplicate.strip() != canonical.strip():
            mapping[duplicate] = canonical
    return mapping


def _merge(driver, duplicate_id: str, canonical_id: str) -> None:
    """Move every relationship off `duplicate` onto `canonical`, then delete it.

    apoc.refactor.mergeNodes keeps all rels + properties on the survivor.
    """
    with driver.session() as session:
        session.run(
            """
            MATCH (dup {id: $dup}), (canon {id: $canon})
            WITH dup, canon WHERE dup <> canon
            CALL apoc.refactor.mergeNodes([canon, dup], {properties: 'discard', mergeRels: true})
            YIELD node RETURN node
            """,
            dup=duplicate_id,
            canon=canonical_id,
        )


def run(labels: list[str], threshold: float, apply: bool) -> None:
    key, base = _load_env()
    driver = _get_neo4j_driver()
    total_candidates = 0
    total_merged = 0
    try:
        for label in labels:
            names = _distinct_names(driver, label)
            pairs = _candidate_pairs(names, key, base, threshold)
            total_candidates += len(pairs)
            print(f"\n[{label}] {len(names)} узлов, {len(pairs)} кандидатов (sim >= {threshold})")
            for a, b, sim in pairs[:15]:
                print(f"    {sim}  {a}  <>  {b}")
            if not apply or not pairs:
                continue
            mapping = _confirm_with_llm(pairs, label, key, base)
            print(f"    LLM подтвердил {len(mapping)} дублей:")
            for dup, canon in mapping.items():
                print(f"      MERGE '{dup}' -> '{canon}'")
                _merge(driver, dup, canon)
                total_merged += 1
    finally:
        driver.close()

    print(f"\n=== ИТОГ: кандидатов {total_candidates}, слито {total_merged} ===")
    if not apply:
        print("(dry-run: LLM-подтверждение и слияние не запускались. Запусти с --apply.)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Semantic/cross-lingual node dedup")
    parser.add_argument("--labels", nargs="+", default=_DEDUP_LABELS)
    parser.add_argument("--threshold", type=float, default=_DEFAULT_THRESHOLD)
    parser.add_argument("--apply", action="store_true", help="confirm with LLM and merge (spends tokens)")
    args = parser.parse_args()
    run(args.labels, args.threshold, args.apply)


if __name__ == "__main__":
    main()
