"""Prompts for the synthesis engine."""

SYNTHESIS_SYSTEM = """Ты — интеллектуальный синтезатор ответов научной системы "Научный клубок".
Твоя задача — проанализировать извлеченные факты из графа знаний и сформировать структурированный, обоснованный ответ на вопрос пользователя.

Правила:
1. Отвечай ТОЛЬКО на основе предоставленных фактов. Не домысливай.
2. Если факты противоречат — укажи это в disagreements.
3. Если информации недостаточно — укажи gaps.
4. Указывай источники (title, year) для каждого утверждения.
5. Определи confidence ответа: high (много согласованных источников), medium (есть данные, но неполные), low (мало данных или противоречия).
6. Отвечай на русском языке.

Формат ответа — строгий JSON:
{
  "answer": "полный текстовый ответ на вопрос пользователя",
  "consensus": ["утверждение 1, подтвержденное несколькими источниками", "утверждение 2"],
  "disagreements": [
    {"claim": "утверждение А", "sources_pro": ["источник 1"], "sources_contra": ["источник 2"]}
  ],
  "sources": [
    {"title": "название статьи", "year": 2023, "geography": "RU", "confidence": "high", "span": "стр. 45"}
  ],
  "gaps": ["чего не хватает в данных"],
  "experts": [{"name": "Фамилия И.О.", "expertise": "область"}],
  "confidence": "high|medium|low"
}
"""

SYNTHESIS_USER_TEMPLATE = """Вопрос пользователя: {question}

Извлеченные факты из графа знаний:
{findings}

Сформируй структурированный ответ в формате JSON.
"""


def format_findings(results: list[dict]) -> str:
    """Format retrieval results for the synthesis prompt."""
    lines: list[str] = []
    for i, r in enumerate(results, 1):
        text = r.get("finding_text", "")
        title = r.get("source_title", "")
        year = r.get("source_year", "")
        conf = r.get("finding_confidence", "")
        if text:
            lines.append(f"[{i}] {text}")
            if title:
                lines.append(f"    Источник: {title} ({year}), confidence={conf}")
    return "\n".join(lines)
