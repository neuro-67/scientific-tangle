# Query pipeline (ML-2)

Парсит вопросы на естественном языке в `QuerySpec` для дальнейшего гибридного поиска.

## Быстрый старт

1. Скопируй `.env.example` в `.env` и подставь свои ключи Yandex AI Studio:

```bash
cp nlp/.env.example nlp/.env
```

2. Запусти парсер одного вопроса:

```bash
python nlp/query_cli.py "методы обессоливания воды: сульфаты/хлориды/Ca/Mg/Na по 200-300 мг/л"
```

3. Запусти тест 4 золотых вопросов:

```bash
python nlp/query/golden_questions_test.py
```

## Структура

- `schemas.py` — Pydantic-модели `QuerySpec`, `NumericConstraint`, `SynthesisResponse`.
- `parser.py` — `QuerySpecParser`, вызывает YandexGPT structured output.
- `prompts.py` — системный промпт и шаблон пользователя.
- `config.py` — env-конфиг.
- `golden_questions_test.py` — тест 4 эталонных вопросов из ТЗ.

## Модель

По умолчанию используется `yandexgpt-5.1` — оптимальный баланс скорости и качества для JSON-извлечения.

## Контракты

Общий контракт между ML-1 (Ingestion) и ML-2 (Query) зафиксирован в [`../EXTRACTION_SCHEMA.md`](../EXTRACTION_SCHEMA.md).

## NER / entity extraction

- `llm_ner_extract.py` — демо извлечения сущностей из текста через YandexGPT 5.1.
- `extraction_gliner.py` — шаблон для GLiNER zero-shot NER (требует `pip install gliner`).
