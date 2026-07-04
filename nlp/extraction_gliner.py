"""GLiNER-based entity extraction template for ML-1.

Requires a stable Python environment (tested on Python 3.10/3.11 + Linux/WSL).
On Windows with Python 3.14 local GLiNER may segfault due to onnxruntime issues,
so this file is provided as a reference implementation for the ingestion worker.

Install:
    pip install gliner

Run:
    python nlp/extraction_gliner.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# GLiNER import is inside try/except so the repo stays importable without it.
try:
    from gliner import GLiNER
except ImportError as exc:  # pragma: no cover
    raise ImportError("Install gliner: pip install gliner") from exc


# Labels must match the project ontology
DEFAULT_LABELS = [
    "Material",
    "Process",
    "Equipment",
    "Property",
    "Condition",
    "Experiment",
    "Publication",
    "Expert",
    "Facility",
    "Finding",
]


def load_model(model_name: str = "urchade/gliner_medium-v2.1") -> GLiNER:
    """Load a GLiNER model."""
    return GLiNER.from_pretrained(model_name)


def extract_entities(
    text: str,
    model: GLiNER,
    labels: list[str] | None = None,
    threshold: float = 0.5,
) -> list[dict]:
    """Extract entities from a text chunk using GLiNER zero-shot NER."""
    labels = labels or DEFAULT_LABELS
    return model.predict_entities(text, labels, threshold=threshold)


def extract_measurements(text: str) -> list[dict]:
    """Rule-based extractor for numeric values and units.

    GLiNER extracts entities but not structured numbers. This helper catches
    patterns like "300 мг/л", "0.8–1.2 м/с", "≤ 1000 мг/дм³".
    """
    # Very basic regex — production version should use pint + LLM verification
    pattern = re.compile(
        r"(?P<operator><=|>=|≤|≥|=)?\s*"
        r"(?P<min>\d+(?:[.,]\d+)?)\s*"
        r"(?:[–—-]\s*(?P<max>\d+(?:[.,]\d+)?))?\s*"
        r"(?P<unit>[a-zA-Zа-яА-Я²³/·%]+)"
    )
    results = []
    for match in pattern.finditer(text):
        groups = match.groupdict()
        operator = "="
        if groups.get("max"):
            operator = "range"
        elif groups.get("operator") in ("<=", "≤"):
            operator = "<="
        elif groups.get("operator") in (">=", "≥"):
            operator = ">="
        results.append(
            {
                "value": None if groups.get("max") else float(groups["min"].replace(",", ".")),
                "min": float(groups["min"].replace(",", ".")) if groups.get("max") else None,
                "max": float(groups["max"].replace(",", ".")) if groups.get("max") else None,
                "operator": operator,
                "unit": groups["unit"],
                "span": {"start": match.start(), "end": match.end()},
            }
        )
    return results


def main() -> int:
    sample_path = Path(__file__).with_name("sample_text.txt")
    text = sample_path.read_text(encoding="utf-8")[:2000]

    model = load_model()
    entities = extract_entities(text, model)
    measurements = extract_measurements(text)

    output = {
        "entities": [
            {
                "type": e["label"],
                "surface": e["text"],
                "canonical": e["text"].lower(),
                "score": e.get("score"),
            }
            for e in entities
        ],
        "measurements": measurements,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
