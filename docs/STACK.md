# Технологический стек «Научный клубок»

Выбор стека подчинён двум ограничениям хакатона: **~1.5 дня на 4 человек** и **соответствие рекомендациям ТЗ** (Neo4j, spaCy/ruBERT/DeepPavlov, Elasticsearch/Vespa, OWL/RDF/SHACL, FAIR). Где рекомендация ТЗ конфликтует со сроками — берём быстрый в реализации вариант, а рекомендованный указываем как production-путь.

---

## Backend

| Компонент | Выбор | Обоснование |
|---|---|---|
| Язык/рантайм | Python 3.11 | Требование заказчика, общий язык с ML |
| Web-фреймворк | **FastAPI** | Требование; async, автогенерация OpenAPI, Pydantic-валидация |
| ASGI-сервер | Uvicorn (+ Gunicorn в prod) | Стандарт для FastAPI |
| Валидация/схемы | Pydantic v2 | Общие схемы запроса/ответа/онтологии |
| Очередь задач | **arq** (Redis) | Легче Celery, async-native, достаточно для ingestion |
| ORM (реляц.) | SQLAlchemy 2 + Alembic | Users/Audit/Jobs/Docs, миграции |
| Драйвер графа | `neo4j` (официальный) | Cypher из Python |
| Auth | JWT (`python-jose`) + argon2 (`passlib`) | RBAC, 5 ролей |
| Логи/метрики | structlog + Prometheus client | Наблюдаемость (НФТ надёжность) |

## Frontend

| Компонент | Выбор | Обоснование |
|---|---|---|
| Язык | **TypeScript** | Требование |
| Фреймворк | **React 18** + Vite | Требование; Vite — быстрый DX |
| UI-kit | Mantine (или MUI) | Готовые компоненты: формы, таблицы, чипы фильтров — экономия времени |
| Данные/кэш | TanStack Query | Кэш запросов, статусы загрузки |
| Роутинг | React Router | SPA-навигация |
| Визуализация графа | **Cytoscape.js** (react-cytoscapejs) | Отрисовка подграфа, цепочки «материал→процесс→оборудование→результат», подсветка противоречий |
| Графики дашбордов | Recharts | Метрики покрытия, активность команд |
| Формы фильтров | React Hook Form | Числовые диапазоны, мультиселекты |

## Данные и хранилища

| Роль | Выбор | Обоснование |
|---|---|---|
| **Граф знаний** | **Neo4j 5 Community** | Рекомендация ТЗ; Cypher, многохоповые обходы, индексы |
| **Векторный поиск** | **Qdrant** | Быстрый старт, HNSW, фильтры по метаданным, payload = провенанс |
| Реляционная БД | **PostgreSQL 16** | Users, Audit, Jobs, метаданные документов, `term_aliases` |
| Кэш + очередь | **Redis 7** | arq-очередь, кэш ответов/эмбеддингов |
| Object storage | **MinIO** (S3 API) | Оригиналы документов; в dev — можно локальная ФС |

> **Про Elasticsearch/Vespa (рекомендация ТЗ):** для гибридного поиска берём Qdrant (вектор) + Neo4j (структура) — этого достаточно и быстрее в сборке. Полнотекстовый BM25 закрываем встроенным full-text index Neo4j. ES/Vespa указываем как альтернативу для масштаба >10M чанков.

## NLP / ML

| Задача | Выбор (MVP) | Production-путь (ТЗ) |
|---|---|---|
| Извлечение сущностей/связей/чисел | **Claude API** structured output (`claude-opus-4-8` для качества, `claude-sonnet-4-6` для потока) | Дообученный **ruBERT/spaCy** NER + rule-based для чисел |
| Синтез ответов (RAG) | Claude (`claude-opus-4-8`) | — |
| Парсинг запроса → QuerySpec | Claude structured output | Гибрид: правила + LLM |
| Эмбеддинги (мультиязык) | **BAAI/bge-m3** или `intfloat/multilingual-e5-large` | fine-tune на доменном корпусе |
| Реранк | RRF (Reciprocal Rank Fusion) | cross-encoder `bge-reranker-v2-m3` |
| Парсинг PDF/DOCX | PyMuPDF + `unstructured` (таблицы) | + GROBID для научных статей |
| Детект языка | `fasttext-langdetect` | — |
| Извлечение чисел/единиц | `pint` (нормализация единиц) + regex + LLM | обучаемый extractor |

> **Почему LLM-извлечение, а не ruBERT в MVP:** обучение NER-модели требует размеченных данных и времени, которых на хакатоне нет. Claude даёт мультиязычность RU/EN «из коробки», извлекает связи и числовые ограничения по JSON-схеме и хорошо канонизирует термины. ML-команда фокусируется на схемах извлечения, качестве retrieval и оценке — а не на разметке. ruBERT/spaCy честно показываем в докладе как путь к удешевлению.

## Онтология / стандарты

| Аспект | Выбор | Обоснование |
|---|---|---|
| Модель онтологии | Прагматичная схема в Neo4j (labels + свойства), задокументированная в **OWL/SHACL-стиле** | Полный OWL-ризонер избыточен для хакатона; SHACL-констрейнты — как валидация на будущее |
| Экспорт | **JSON-LD** (+ Markdown) | FAIR: Interoperable; PDF — если останется время |
| Идентификаторы | стабильные URI узлов | FAIR: Findable |

## Инфраструктура и DevOps

| Компонент | Выбор | Обоснование |
|---|---|---|
| Оркестрация (dev/demo) | **docker-compose** | Один `up` поднимает всё → «развёрнутое решение» для жюри |
| Контейнеры | Docker | Стандарт |
| CI (опц.) | GitHub Actions (lint + build) | Если останется время |
| Хостинг демо | VPS / Yandex Cloud / Render | Ссылка для жюри (требование сдачи) |
| Конфиг | pydantic-settings + `.env` | Секреты, ключи API |

## Инструменты разработки

- **Python:** uv (или poetry), ruff (lint+format), mypy, pytest.
- **TS:** pnpm, eslint, prettier, vitest.
- **Общее:** pre-commit hooks, `.env.example`, Makefile с целями `up/seed/ingest/dev`.

---

## Сводка «что запускается» (docker-compose services)

```
frontend        React SPA (Vite preview / nginx)
backend         FastAPI (uvicorn)
worker          arq NLP/ingestion воркер
neo4j           граф знаний
qdrant          векторы
postgres        реляционные данные
redis           очередь + кэш
minio           object storage
```

Внешняя зависимость: **Claude API** (ключ в `.env`). Всё остальное — локально в compose.
