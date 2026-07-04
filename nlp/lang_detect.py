"""Language detection (docs/NLP_PIPELINE.md [2]: "fasttext-langdetect на
уровне блока. Метка lang ∈ {ru, en} идёт в чанк").

Uses `langdetect` (pure Python, no model download) instead of the
documented `fasttext-langdetect`: same class of pragmatic substitution as
recursive_split() replacing langchain_text_splitters earlier this session
(that one for a segfault, this one to avoid pulling in another ~1GB model
under hackathon time pressure) -- same {ru, en} output contract either way.
"""

from __future__ import annotations

from langdetect import LangDetectException, detect
from langdetect.detector_factory import DetectorFactory

# Deterministic results (langdetect's default is seeded by wall-clock time,
# which would make the same chunk classify differently between runs).
DetectorFactory.seed = 0


def detect_language(text: str) -> str:
    """Return 'ru', 'en', or 'unknown' (short/ambiguous text, e.g. a bare
    entity name or a numeric-only fragment)."""
    text = text.strip()
    if len(text) < 20:
        return "unknown"
    try:
        lang = detect(text)
    except LangDetectException:
        return "unknown"
    return lang if lang in ("ru", "en") else "unknown"
