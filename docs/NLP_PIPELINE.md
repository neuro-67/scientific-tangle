# NLP-пайплайн «Научный клубок»

Два пайплайна: **Ingestion** (документ → граф, offline) и **Query** (вопрос → структурированные фильтры, online). Оба используют Claude structured output как рабочую лошадку MVP; ruBERT/spaCy — production-путь для удешевления потока.

---

## A. Ingestion-пайплайн (документ → граф)

```
[1] Parse → [2] Language → [3] Chunk → [4] Extract → [5] Normalize
→ [6] Resolve → [7] Embed → [8] Write(Neo4j+Qdrant) → [9] Status
```

### [1] Parse — разбор документа
- **PDF:** PyMuPDF (текст + координаты) + `unstructured` для таблиц (важно: числовые параметры часто в таблицах).
- **DOCX:** `python-docx` / `unstructured`.
- Сохраняем `span` (страница, офсет) для каждого блока → провенанс.

### [2] Language detection
- `fasttext-langdetect` на уровне блока. Метка `lang ∈ {ru, en}` идёт в чанк и влияет на промпт (RU/EN оба поддержаны).

### [3] Chunking
- Семантические чанки ~800 токенов, overlap ~120. Таблицы — отдельными чанками целиком (не рвать).
- Каждый чанк: `{doc_id, page, offset, lang, text}`.

### [4] Extraction — сердце пайплайна (Claude structured output)
Один вызов на чанк с JSON-схемой по онтологии. Модель: `claude-sonnet-4-6` для потока, `claude-opus-4-8` для сложных/табличных чанков.

Целевая схема ответа:
```json
{
  "entities": [
    {"type": "Material", "surface": "католит", "canonical": "католит", "attrs": {}},
    {"type": "Process", "surface": "electrowinning", "canonical": "электроэкстракция"}
  ],
  "measurements": [
    {"property": "сульфаты", "operator": "<=", "value": 300, "unit": "мг/л",
     "applies_to_surface": "исходная вода"}
  ],
  "conditions": [{"name": "климат", "value": "холодный"}],
  "relations": [
    {"head": "электроэкстракция", "type": "uses_material", "tail": "католит",
     "evidence": "…цитата…"}
  ],
  "findings": [
    {"statement": "оптимальная скорость циркуляции католита 0.8–1.2 м/с",
     "confidence": "medium"}
  ]
}
```
Правила промпта:
- Извлекать **только явно присутствующее** в тексте (никаких домыслов) — критично для точности чисел (НФТ).
- Для каждого factа возвращать `evidence` (цитата) → провенанс и защита от галлюцинаций.
- Числа отдавать структурно: `operator/value/min/max/unit`, не строкой.

### [5] Normalize — канонизация терминов и единиц
- **Термины:** lookup в `term_aliases` (Postgres) + эмбеддинг-матч, если alias нет. `electrowinning → электроэкстракция`, `ПВП → печь взвешенной плавки`.
- **Единицы:** `pint` приводит к канон. единице (`мг/дм³ → мг/л`, `°C`, `м/с`). Ошибка конверсии → факт помечается `low` и в ревью.
- Результат — `canonical_name`, которое станет ключом узла графа.

### [6] Entity Resolution — дедуп
- Матч извлечённой сущности к существующему узлу: точное совпадение `canonical_name` → иначе эмбеддинг-similarity (порог) + fuzzy (`rapidfuzz`).
- Совпало → `MERGE` в существующий узел; не совпало → новый узел.
- Предотвращает «никель» и «Ni» как два разных материала.

### [7] Embedding
- `bge-m3` (мультиязычный) для чанков и для карточек сущностей (`canonical_name + контекст`).
- Пишем в Qdrant с payload: `{doc_id, page, lang, geography, sensitivity, entity_ids[]}` — payload используется как фильтр при поиске.

### [8] Write — запись в граф + векторы
- Neo4j: `MERGE` узлов по ключу, `CREATE` связей с провенансом (`Source`, `confidence`, `geography`, `valid_from`, `extracted_at`).
- Всё в рамках одной doc-транзакции провенанса → идемпотентность и откат при ошибке.

### [9] Status / Errors
- Postgres `documents.status`: `queued → processing → done | failed`.
- `failed` хранит причину и шаг; ретрай с backoff; dead-letter в Redis.
- Метрики: чанков обработано, сущностей/связей извлечено, доля `low`-confidence.

---

## B. Query-пайплайн (вопрос → ответ)

```
[1] Parse Query → [2] Retrieve(vector+graph+numeric) → [3] Merge/Rerank
→ [4] Assemble → [5] Synthesize → [6] Subgraph → [7] Audit
```

### [1] Query Parsing → QuerySpec (Claude structured output)
Вопрос на естественном языке → структура фильтров:
```json
{
  "intent": "review",            // search | review | compare | gap
  "materials": ["сульфаты", "хлориды"],
  "processes": ["обессоливание"],
  "geography": "any",            // RU | foreign | any
  "time_range": {"from": 2020, "to": 2025},
  "numeric_constraints": [
    {"property": "сульфаты", "operator": "range", "min": 200, "max": 300, "unit": "мг/л"},
    {"property": "сухой остаток", "operator": "<=", "value": 1000, "unit": "мг/л"}
  ],
  "compare": null
}
```
Термины в QuerySpec тоже канонизируются через `term_aliases`.

### [2] Retrieve — гибридный поиск (параллельно)
- **(a) Vector** — эмбеддинг запроса → Qdrant top-k, с payload-фильтрами (geography/sensitivity/lang).
- **(b) Graph** — Cypher по QuerySpec: обход `applies_to / uses_material / operates_at_condition / produces_output / described_in` на 3–4 хопа.
- **(c) Numeric** — фильтр `Measurement`-узлов по `min/max/operator` (точные сравнения диапазонов).
- RBAC-фильтр `sensitivity` применяется во всех трёх ветках.

### [3] Merge / Rerank
- Объединение кандидатов из трёх ветвей, дедуп по узлам.
- **RRF** (Reciprocal Rank Fusion) для MVP; cross-encoder `bge-reranker-v2-m3` — если останется время.

### [4] Assemble context
- Собираем: факты графа (с провенансом) + подтверждающие чанки + метаданные источников.
- Группируем по методу/году/географии для intent=review.

### [5] Synthesize (Claude `claude-opus-4-8`)
Структурированный ответ:
```json
{
  "answer": "…связный текст…",
  "consensus": ["вывод, подтверждённый ≥N источниками"],
  "disagreements": [{"point": "…", "sources_a": [...], "sources_b": [...]}],
  "sources": [{"title": "...", "year": 2024, "geography": "foreign", "confidence": "medium", "span": "p.42"}],
  "gaps": ["нет экспериментов: холодный климат + кучное выщелачивание + Ni-руда"],
  "experts": [{"name": "...", "affiliation": "..."}],
  "confidence": "medium"
}
```
Требование к промпту: **каждое утверждение ссылается на источник** из контекста; если данных нет — честно писать «пробел», а не выдумывать.

### [6] Subgraph для визуализации
- Возврат узлов/связей, участвовавших в ответе → фронт рисует цепочку «материал→процесс→оборудование→результат» и подсвечивает `contradicts`.

### [7] Audit + Cache
- Лог запроса в Postgres (`audit_log`); кэш ответа в Redis по хэшу нормализованного QuerySpec.

---

## C. Оценка качества (для доклада)

- **Извлечение:** ручная разметка 30–50 чанков → precision/recall по сущностям и числам (акцент на числа — НФТ «ошибки недопустимы»).
- **Retrieval:** набор из ~15 эталонных вопросов из ТЗ → hit@k, наличие нужного источника в контексте.
- **Ответ:** экспертная оценка faithfulness (нет утверждений без источника) и полноты.

---

## D. Разделение работ ML-команды

| ML-1 | ML-2 |
|---|---|
| Ingestion: parse/chunk/extract, схемы извлечения, нормализация единиц (`pint`) | Query: parsing→QuerySpec, гибридный retrieval, синтез-промпт |
| Entity resolution, `term_aliases`, канонизация | Эмбеддинги/Qdrant, RRF-реранк, кэш |
| Запись в Neo4j (совместно с Backend) | Оценка качества, эталонные вопросы |
