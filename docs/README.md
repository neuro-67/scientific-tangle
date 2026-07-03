# Документация «Научный клубок»

Единая карта знаний R&D для горно-металлургической отрасли (GraphRAG).

| Документ | О чём |
|---|---|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Архитектура системы: сервисы, потоки данных ingestion/query, провенанс, RBAC, границы MVP |
| [STACK.md](./STACK.md) | Технологический стек с обоснованием выбора и production-путями |
| [NLP_PIPELINE.md](./NLP_PIPELINE.md) | Два NLP-пайплайна (ingestion и query), схемы извлечения, оценка качества |
| [ONTOLOGY.md](./ONTOLOGY.md) | Онтология: типы сущностей, связи, провенанс, индексы, gap-detection |
| [ROADMAP.md](./ROADMAP.md) | План на ~1.5 дня, роли, фазы, gate-чекпоинты, риски, чеклист сдачи |

## TL;DR

- **Паттерн:** GraphRAG — NLP-извлечение → граф знаний (Neo4j) + векторы (Qdrant) → гибридный поиск → синтез ответа с цитатами.
- **Backend:** FastAPI + Postgres + Redis + arq. **Frontend:** React/TS + Cytoscape.
- **NLP (MVP):** Claude structured output для извлечения и синтеза; ruBERT/spaCy — production-путь.
- **Развёртывание:** один `docker compose up`.

## Структура монорепо

```
scientific-tangle/
├── docs/          ← вы здесь: архитектура, стек, roadmap, онтология, nlp
├── backend/       FastAPI: API, auth/RBAC, оркестратор запроса, аудит
├── frontend/      React + TS: поиск, ответ, граф, дашборды
├── nlp/           ingestion + query пайплайны, extraction-схемы
├── infra/         docker-compose, конфиги сервисов
└── data/          корпус, каталог экспериментов, справочники
```
