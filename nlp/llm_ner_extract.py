"""Demo: extract entities from a PDF text chunk using YandexGPT 5.1.

This is what ML-1 ingestion would do per chunk.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from nlp.query.parser import QuerySpecParser


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

EXTRACTION_SYSTEM_PROMPT = """Ты — NLP-извлекатель для научной системы "Научный клубок".
Извлеки из фрагмента текста сущности, связи и числовые ограничения по онтологии.

Типы сущностей:
- Material (вещества, материалы): сульфаты, хлориды, католит, никель, магнетит
- Process (технологические процессы): обессоливание, электроэкстракция, обезвоживание
- Equipment (оборудование): фильтр-пресс, печь, насос
- Property (свойство/параметр): концентрация, температура, скорость, сухой остаток
- Measurement (числовое значение): включает value/min/max/unit/operator
- Condition (условие): холодный климат, кучное выщелачивание
- Experiment (опыт/протокол)
- Publication (публикация/отчёт/патент)
- Expert (автор)
- Facility (лаборатория/предприятие)
- Finding (вывод/эффект)

Верни строго JSON по схеме:
{
  "entities": [
    {"type": "Material", "surface": "...", "canonical": "..."}
  ],
  "measurements": [
    {"property": "...", "operator": "<=|>=|=|range", "value": число или null, "min": ..., "max": ..., "unit": "...", "applies_to_surface": "..."}
  ],
  "relations": [
    {"head": "...", "type": "uses_material|operates_at_condition|has_measurement|produces_output", "tail": "...", "evidence": "..."}
  ],
  "findings": [
    {"statement": "...", "confidence": "high|medium|low"}
  ]
}

Правила:
1. Извлекай только то, что явно есть в тексте.
2. Для каждого факта возвращай evidence (цитата из текста).
3. Числа отдавай структурно: operator/value/min/max/unit.
4. Канонизируй термины и единицы (мг/дм³ → мг/л).
5. Если данных нет — используй пустые массивы."""


def extract_from_text(text: str) -> dict:
    parser = QuerySpecParser()
    payload = parser._build_payload(text)  # reuse auth/config
    payload["messages"][0]["text"] = EXTRACTION_SYSTEM_PROMPT
    payload["messages"][1]["text"] = f"Фрагмент текста:\n{text}\n\nВерни JSON:"
    response = parser._session.post(
        f"{parser._config.yandex_base_url}/foundationModels/v1/completion",
        json=payload,
        timeout=120,
    )
    response.raise_for_status()
    raw_text = parser._extract_text(response.json())
    cleaned = parser._clean_json(raw_text)
    return json.loads(cleaned)


def main() -> int:
    text_path = Path(__file__).parent / "sample_text.txt"
    text = text_path.read_text(encoding="utf-8")
    # Use a manageable chunk (first ~3000 chars)
    chunk = text[:3000]
    result = extract_from_text(chunk)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
