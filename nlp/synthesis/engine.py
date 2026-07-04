"""Synthesis engine using YandexGPT to generate structured answers from retrieved findings."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import requests

from nlp.query.config import QueryConfig
from nlp.synthesis.prompts import SYNTHESIS_SYSTEM, SYNTHESIS_USER_TEMPLATE, format_findings
from nlp.query.schemas import SynthesisResponse

logger = logging.getLogger(__name__)


class SynthesisEngine:
    """Generates a structured answer from retrieved findings via the configured LLM provider."""

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

    def synthesize(self, question: str, findings: list[dict[str, Any]]) -> SynthesisResponse:
        """Synthesize a structured answer from findings via the configured LLM provider."""
        if not findings:
            return SynthesisResponse(
                answer="No data found in the knowledge graph for this query.",
                consensus=[],
                disagreements=[],
                sources=[],
                gaps=["No data in the graph for this query"],
                experts=[],
                confidence="low",
            )

        if self._config.provider == "none":
            logger.warning("No LLM provider configured, using fallback synthesis")
            return self._fallback_synthesize(question, findings)

        findings_text = format_findings(findings)
        user_text = SYNTHESIS_USER_TEMPLATE.format(question=question, findings=findings_text)
        try:
            raw_text = self._complete(SYNTHESIS_SYSTEM, user_text)
            cleaned = self._clean_json(raw_text)
            parsed = json.loads(cleaned)
            return SynthesisResponse.model_validate(parsed)
        except Exception:
            logger.exception("synthesis failed", extra={"question": question})
            return self._fallback_synthesize(question, findings)

    def _complete(self, system_text: str, user_text: str) -> str:
        if self._config.provider == "routerai":
            return self._complete_routerai(system_text, user_text)
        return self._complete_yandex(system_text, user_text)

    def _complete_routerai(self, system_text: str, user_text: str) -> str:
        payload = {
            "model": self._config.routerai_model,
            "messages": [
                {"role": "system", "content": system_text},
                {"role": "user", "content": user_text},
            ],
            "temperature": 0.2,
            "max_tokens": self._config.routerai_max_tokens,
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

    def _complete_yandex(self, system_text: str, user_text: str) -> str:
        model_uri = f"gpt://{self._config.yandex_folder_id}/{self._config.yandex_model}"
        payload = {
            "modelUri": model_uri,
            "completionOptions": {
                "stream": False,
                "temperature": 0.2,
                "maxTokens": 2000,
            },
            "messages": [
                {"role": "system", "text": system_text},
                {"role": "user", "text": user_text},
            ],
        }
        response = self._session.post(
            f"{self._config.yandex_base_url}/foundationModels/v1/completion",
            json=payload,
            timeout=30,
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

    def _fallback_synthesize(
        self, question: str, findings: list[dict[str, Any]]
    ) -> SynthesisResponse:
        """Lightweight fallback when LLM call fails."""
        from nlp.query.schemas import SourceCitation

        fragments: list[str] = []
        sources: list[SourceCitation] = []
        for r in findings[:5]:
            text = r.get("finding_text")
            if text:
                fragments.append(text)
            sources.append(
                SourceCitation(
                    title=r.get("source_title"),
                    year=r.get("source_year"),
                    geography=r.get("source_geography"),
                    confidence="high" if r.get("finding_confidence", 0) > 0.7 else "medium",
                )
            )

        answer = "\n\n".join(fragments) if fragments else "Найдены связанные данные, но выводы требуют уточнения."

        return SynthesisResponse(
            answer=answer,
            consensus=[],
            disagreements=[],
            sources=sources,
            gaps=[],
            experts=[],
            confidence="medium" if len(findings) > 3 else "low",
        )
