# Query pipeline (ML-2)

Парсит вопросы на естественном языке в `QuerySpec` для дальнейшего гибридного поиска.
Подробный статус реализации, найденные баги и известные ограничения — в [`../README.md`](../README.md).

## Быстрый старт

1. Скопируй корневой `.env.example` в `.env` и подставь ключи:

```bash
cp .env.example .env
```

`ROUTERAI_API_KEY` — если задан, используется вместо Yandex (Yandex AI Studio сейчас недоступен,
RouterAI — fallback-провайдер, OpenAI-совместимый). `YANDEX_API_KEY` — если RouterAI не задан.
Ни один не задан → rule-based fallback без LLM. См. `nlp/query/config.py::QueryConfig.provider`.

2. Запусти парсер одного вопроса:

```bash
python nlp/query_cli.py "методы обессоливания воды: сульфаты/хлориды/Ca/Mg/Na по 200-300 мг/л"
```

3. Запусти тест 4 золотых вопросов:

```bash
python nlp/query/golden_questions_test.py
```

## Структура

- `schemas.py` — Pydantic-модели `QuerySpec`, `NumericConstraint`, `SynthesisResponse` (включая
  `recommendations` и `extracted_at` — верификация знаний и рекомендации из ТЗ).
- `parser.py` — `QuerySpecParser`, провайдер-агностичный (`complete()` работает и с RouterAI, и с Yandex).
- `prompts.py` — системный промпт и шаблон пользователя.
- `config.py` — env-конфиг, выбор провайдера.
- `golden_questions_test.py` — тест 4 эталонных вопросов из ТЗ.
- `retrieval/` — `HybridRetrievalEngine` (Qdrant + Neo4j + RRF), `Neo4jClient`, `QdrantSearchClient`.
  Реальный синтез-движок — `nlp/synthesis/engine.py`, НЕ `retrieval/synthesis.py` (см. `../README.md`).

## Модель

По умолчанию (RouterAI) — `google/gemini-3.1-flash-lite`: самая быстрая из протестированных моделей
для парсинга/синтеза на живом пути с SLA 3-5с (`docs/ARCHITECTURE.md`). Обоснование выбора и цифры
бенчмарка — в `../README.md`.

## Контракты

Общий контракт между ML-1 (Ingestion) и ML-2 (Query) зафиксирован в [`../EXTRACTION_SCHEMA.md`](../EXTRACTION_SCHEMA.md).

## NER / entity extraction

- `llm_ner_extract.py` — демо извлечения сущностей из текста через YandexGPT 5.1.
- `extraction_gliner.py` — шаблон для GLiNER zero-shot NER (требует `pip install gliner`).
