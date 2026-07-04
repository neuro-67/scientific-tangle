"""Quick test of the four golden questions from the task."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from nlp.query.parser import QuerySpecParser


def _load_env_file(path: Path) -> None:
    """Minimal .env loader without extra dependencies."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key, value)


_load_env_file(Path(__file__).parent.parent / ".env")

QUESTIONS = [
    "методы обессоливания воды: сульфаты/хлориды/Ca/Mg/Na по 200-300 мг/л, сухой остаток <=1000 мг/дм3",
    "оптимальная скорость циркуляции католита в процессе электроэкстракции",
    "извлечение Au, Ag и металлов платиновой группы из руд",
    "закачка воды в горные выработки: методы и оборудование",
]

parser = QuerySpecParser()
results = []
for q in QUESTIONS:
    print(f"\n=== ВОПРОС: {q} ===")
    try:
        spec = parser.parse(q)
        dumped = spec.model_dump(by_alias=True)
        print(json.dumps(dumped, ensure_ascii=False, indent=2))
        results.append({"question": q, "spec": dumped})
    except Exception as e:
        print(f"ERROR: {e}")
        results.append({"question": q, "error": str(e)})

Path("golden_questions_test.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("\nSaved to golden_questions_test.json")
