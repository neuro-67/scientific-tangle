"""YandexGPT-based QuerySpec parser with full ontology coverage.

Includes a rule-based fallback for offline/demo use when the LLM API
is unavailable or no API key is configured.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import requests

from nlp.query.config import QueryConfig
from nlp.query.prompts import QUERY_SPEC_SYSTEM, QUERY_SPEC_USER_TEMPLATE
from nlp.query.schemas import QuerySpec, Geography, TimeRange, QueryIntent

logger = logging.getLogger(__name__)

# Simple keyword maps for rule-based extraction
_MATERIAL_KEYWORDS = {
    "золото", "серебро", "медь", "железо", "алюминий", "никель", "платина",
    "уголь", "нефть", "газ", "руда", "концентрат", "шлак", "сплав",
    "gold", "silver", "copper", "iron", "aluminum", "nickel", "platinum",
    "coal", "oil", "gas", "ore", "concentrate", "slag", "alloy",
}

_PROCESS_KEYWORDS = {
    "добыча", "переработка", "обогащение", "выщелачивание", "флотация",
    "гидрометаллургия", "пирометаллургия", "электролиз", "осаждение",
    "mining", "extraction", "processing", "beneficiation", "leaching",
    "flotation", "hydrometallurgy", "pyrometallurgy", "electrolysis",
}

_EQUIPMENT_KEYWORDS = {
    "дробилка", "мельница", "флотомашина", "смеситель", "реактор",
    "конвейер", "насос", "сито", "сепаратор", "печь",
    "crusher", "mill", "flotation machine", "mixer", "reactor",
    "conveyor", "pump", "screen", "separator", "furnace",
}

_GEOGRAPHY_MAP = {
    "россия": Geography.RU,
    "russia": Geography.RU,
    "ru": Geography.RU,
    "российская": Geography.RU,
    "снг": Geography.RU,
    "зарубеж": Geography.FOREIGN,
    "foreign": Geography.FOREIGN,
    "international": Geography.FOREIGN,
    "международный": Geography.FOREIGN,
}

_INTENT_MAP = {
    "compare": QueryIntent.COMPARE,
    "сравн": QueryIntent.COMPARE,
    "difference": QueryIntent.COMPARE,
    "vs": QueryIntent.COMPARE,
    "versus": QueryIntent.COMPARE,
    "gap": QueryIntent.GAP,
    "пробел": QueryIntent.GAP,
    "недостаток": QueryIntent.GAP,
    "review": QueryIntent.REVIEW,
    "обзор": QueryIntent.REVIEW,
    "search": QueryIntent.SEARCH,
    "поиск": QueryIntent.SEARCH,
    "найти": QueryIntent.SEARCH,
}


def _rule_based_parse(question: str) -> QuerySpec:
    """Extract QuerySpec using simple keyword matching."""
    q_lower = question.lower()
    
    materials = [w for w in _MATERIAL_KEYWORDS if w in q_lower]
    processes = [w for w in _PROCESS_KEYWORDS if w in q_lower]
    equipment = [w for w in _EQUIPMENT_KEYWORDS if w in q_lower]
    
    # Geography detection
    geography = Geography.ANY
    for key, geo in _GEOGRAPHY_MAP.items():
        if key in q_lower:
            geography = geo
            break
    
    # Intent detection
    intent = QueryIntent.SEARCH
    for key, intent_val in _INTENT_MAP.items():
        if key in q_lower:
            intent = intent_val
            break
    
    # Year range detection
    years = [int(y) for y in re.findall(r'\b(19\d{2}|20\d{2})\b', question)]
    time_range = TimeRange()
    if years:
        time_range = TimeRange(from_year=min(years), to_year=max(years))
    
    return QuerySpec(
        intent=intent,
        materials=materials,
        processes=processes,
        equipment=equipment,
        geography=geography,
        time_range=time_range,
    )


class QuerySpecParser:
    """Parses a natural-language question into a structured QuerySpec."""

    def __init__(self, config: QueryConfig | None = None) -> None:
        self._config = config or QueryConfig()
        self._session = requests.Session()
        if self._config.provider == "routerai":
            self._session.headers.update(
                {
                    "Authorization": f"Bearer {self._config.routerai_api_key}",
                    "Content-Type": "application/json",
                }
            )
        elif self._config.provider == "yandex":
            self._session.headers.update(
                {
                    "Authorization": f"Api-Key {self._config.yandex_api_key}",
                    "Content-Type": "application/json",
                }
            )

    def parse(self, question: str) -> QuerySpec:
        """Parse question into QuerySpec via the configured LLM provider or fallback."""
        if self._config.provider == "none":
            logger.warning("No LLM provider configured, using rule-based parser")
            return _rule_based_parse(question)

        try:
            raw_text = self.complete(
                QUERY_SPEC_SYSTEM, QUERY_SPEC_USER_TEMPLATE.format(question=question)
            )
            cleaned = self._clean_json(raw_text)
            parsed = json.loads(cleaned)
            return QuerySpec.model_validate(parsed)
        except Exception as exc:
            logger.warning("LLM parse failed (%s), falling back to rule-based", exc)
            return _rule_based_parse(question)

    def complete(self, system_text: str, user_text: str, max_tokens: int | None = None) -> str:
        """Provider-agnostic completion call, shared with SynthesisEngine."""
        if self._config.provider == "routerai":
            return self._complete_routerai(system_text, user_text, max_tokens)
        if self._config.provider == "yandex":
            return self._complete_yandex(system_text, user_text, max_tokens)
        raise RuntimeError("No LLM provider configured")

    def _complete_routerai(self, system_text: str, user_text: str, max_tokens: int | None) -> str:
        payload = {
            "model": self._config.routerai_model,
            "messages": [
                {"role": "system", "content": system_text},
                {"role": "user", "content": user_text},
            ],
            "temperature": self._config.routerai_temperature,
            "max_tokens": max_tokens or self._config.routerai_max_tokens,
        }
        response = self._session.post(
            f"{self._config.routerai_base_url}/chat/completions",
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise ValueError("No choices in RouterAI response")
        return choices[0].get("message", {}).get("content", "")

    def _complete_yandex(self, system_text: str, user_text: str, max_tokens: int | None) -> str:
        model_uri = f"gpt://{self._config.yandex_folder_id}/{self._config.yandex_model}"
        payload = {
            "modelUri": model_uri,
            "completionOptions": {
                "stream": False,
                "temperature": self._config.yandex_temperature,
                "maxTokens": max_tokens or self._config.yandex_max_tokens,
            },
            "messages": [
                {"role": "system", "text": system_text},
                {"role": "user", "text": user_text},
            ],
        }
        response = self._session.post(
            f"{self._config.yandex_base_url}/foundationModels/v1/completion",
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        return self._extract_text(response.json())

    @staticmethod
    def _extract_text(data: dict[str, Any]) -> str:
        alternatives = data.get("result", {}).get("alternatives", [])
        if not alternatives:
            raise ValueError("No alternatives in LLM response")
        return alternatives[0].get("message", {}).get("text", "")

    @staticmethod
    def _clean_json(raw: str) -> str:
        """Strip markdown code fences and extra whitespace."""
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        return cleaned.strip()
