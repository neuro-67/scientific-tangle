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
    """Generates a structured answer from retrieved findings using YandexGPT."""

    def __init__(self, config: QueryConfig | None = None) -> None:
        self._config = config or QueryConfig()
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Api-Key {self._config.yandex_api_key}",
                "Content-Type": "application/json",
            }
        )

    def synthesize(self, question: str, findings: list[dict[str, Any]]) -> SynthesisResponse:
        """Synthesize a structured answer from findings via YandexGPT."""
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

        if not self._config.yandex_api_key:
            logger.warning("No Yandex API key configured, using fallback synthesis")
            return self._fallback_synthesize(question, findings)

        payload = self._build_payload(question, findings)
        try:
            response = self._session.post(
                f"{self._config.yandex_base_url}/foundationModels/v1/completion",
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            raw_text = self._extract_text(data)
            cleaned = self._clean_json(raw_text)
            parsed = json.loads(cleaned)
            return SynthesisResponse.model_validate(parsed)
        except Exception as exc:
            logger.exception("synthesis failed", extra={"question": question})
            return self._fallback_synthesize(question, findings)

    def _build_payload(self, question: str, findings: list[dict[str, Any]]) -> dict[str, Any]:
        model_uri = f"gpt://{self._config.yandex_folder_id}/{self._config.yandex_model}"
        findings_text = format_findings(findings)
        return {
            "modelUri": model_uri,
            "completionOptions": {
                "stream": False,
                "temperature": 0.2,
                "maxTokens": 2000,
            },
            "messages": [
                {"role": "system", "text": SYNTHESIS_SYSTEM},
                {
                    "role": "user",
                    "text": SYNTHESIS_USER_TEMPLATE.format(
                        question=question, findings=findings_text
                    ),
                },
            ],
        }

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
