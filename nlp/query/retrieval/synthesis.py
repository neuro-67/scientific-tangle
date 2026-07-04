"""Synthesis: generate structured answer from retrieved context."""

from __future__ import annotations

import json

from nlp.query.parser import QuerySpecParser
from nlp.query.schemas import SynthesisResponse


SYNTHESIS_SYSTEM_PROMPT = """Ты — научный ассистент системы "Научный клубок".
На основе предоставленного контекста сформируй структурированный ответ на вопрос пользователя.

Правила:
1. Каждое утверждение должно ссылаться на источник из контекста.
2. Если данных недостаточно — честно укажи пробел, не выдумывай.
3. Различай отечественную (RU) и зарубежную (foreign) практику.
4. Для числовых параметров указывай диапазоны и единицы.
5. Выдели консенсус (согласие источников) и противоречия (несогласие).

Верни строго JSON по схеме:
{
  "answer": "...связный текст...",
  "consensus": ["вывод, подтверждённый ≥2 источниками"],
  "disagreements": [{"point": "...", "sources_a": ["..."], "sources_b": ["..."]}],
  "sources": [{"title": "...", "year": 2024, "geography": "foreign", "confidence": "medium", "span": "p.42"}],
  "gaps": ["нет экспериментов: холодный климат + кучное выщелачивание + Ni-руда"],
  "experts": [{"name": "...", "affiliation": "..."}],
  "confidence": "medium"
}"""


class SynthesisEngine:
    """Generates structured answers from retrieved context."""

    def __init__(self, parser: QuerySpecParser | None = None) -> None:
        self._parser = parser or QuerySpecParser()

    def synthesize(
        self,
        query: str,
        context: list[dict],
    ) -> SynthesisResponse:
        """Generate answer from query and retrieved context."""
        # Build context string
        context_str = self._format_context(context)

        # Build payload using parser's config
        payload = self._parser._build_payload(query)
        payload["messages"][0]["text"] = SYNTHESIS_SYSTEM_PROMPT
        payload["messages"][1]["text"] = (
            f"Вопрос: {query}\n\n"
            f"Контекст:\n{context_str}\n\n"
            f"Верни JSON:"
        )

        response = self._parser._session.post(
            f"{self._parser._config.yandex_base_url}/foundationModels/v1/completion",
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        raw_text = self._parser._extract_text(response.json())
        cleaned = self._parser._clean_json(raw_text)
        parsed = json.loads(cleaned)
        return SynthesisResponse.model_validate(parsed)

    def _format_context(self, context: list[dict]) -> str:
        """Format retrieved context for LLM prompt."""
        parts = []
        for i, item in enumerate(context, 1):
            text = item.get("text", "")
            source = item.get("source_title", "Неизвестный источник")
            year = item.get("source_year", "")
            geo = item.get("source_geo", "")
            span = item.get("span", "")
            confidence = item.get("confidence", "medium")

            part = f"[{i}] {text}\n"
            part += f"    Источник: {source}"
            if year:
                part += f", {year}"
            if geo:
                part += f" ({geo})"
            if span:
                part += f", {span}"
            part += f", достоверность: {confidence}"
            parts.append(part)

        return "\n\n".join(parts)
