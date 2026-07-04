# Научный клубок

Единая карта знаний R&D для горно-металлургической отрасли. Связывает публикации, эксперименты, технологические решения, материалы, оборудование, экспертов и выводы в один граф знаний и отвечает на сложные многопараметрические запросы на естественном языке — с цитатами, уровнем достоверности, различением отечественной/зарубежной практики и подсветкой пробелов.

## Как это работает

**GraphRAG:** NLP-пайплайн извлекает из документов сущности, связи и числовые ограничения → пишет в граф знаний (Neo4j) + векторное хранилище (Qdrant) → запрос парсится в структурированные фильтры → гибридный поиск (вектор + обход графа + числовые диапазоны) → LLM синтезирует ответ с провенансом.

## Документация

Подробности — в [`docs/`](./docs/README.md): архитектура, стек, NLP-пайплайн, онтология, roadmap, авторизация/роли ([`docs/backend/AUTH.md`](./docs/backend/AUTH.md)).

> **Агентам:** прежде чем менять код, читайте `docs/` — там нормативные документы (архитектура, code style, доменные модели). README — только верхнеуровневый обзор.

## Быстрый старт

```bash
cp .env.example .env                    # прописать LLM_API_KEY, JWT_SECRET и т.д.
docker compose up -d --build            # инфра + бекенд

# сид локального админа (dev-креды admin / admin)
docker compose exec backend python -m app.cli.seed_admin --username admin --password admin --reset-password


# закачка из дампа в бд
docker compose exec backend sh -lc 'python -m nlp.ingestion.qdrant_upload /app/nlp/corpus_test_results/*_graph.json'

docker compose exec backend sh -lc 'python -m nlp.ingestion.neo4j_import /app/nlp/corpus_test_results/*_graph.json'
# API:      http://localhost:8000/docs
# frontend: http://localhost:5173 (запускается отдельно)
```

Полный список флагов сид-команды и модель ролей — в [`docs/backend/AUTH.md`](./docs/backend/AUTH.md).

## Стек

FastAPI · React/TypeScript · Neo4j · Qdrant · PostgreSQL · MinIO · LLM API · Docker Compose.

## Команда

4 человека: 2 fullstack + 2 ML. Распределение задач — в [`docs/ROADMAP.md`](./docs/ROADMAP.md).
