# NLP-пайплайн — ML-1 (Ingestion) + ML-2 (Query)

Реализация двух пайплайнов из [`docs/NLP_PIPELINE.md`](../docs/NLP_PIPELINE.md) (архитектура/дизайн)
и [`docs/ONTOLOGY.md`](../docs/ONTOLOGY.md) (типы сущностей/связей). Этот файл — про то,
**что реально реализовано, чем это протестировано и какие у этого известные ограничения**.

## LLM-провайдер: RouterAI как fallback на Yandex Studio

Yandex AI Studio недоступен. `nlp/query/config.py::QueryConfig.provider` выбирает провайдера
по наличию переменных окружения:

1. `ROUTERAI_API_KEY` установлен → RouterAI (OpenAI-совместимый прокси, `https://routerai.ru/api/v1`).
2. Иначе `YANDEX_API_KEY` установлен → YandexGPT.
3. Иначе → rule-based fallback (простой keyword-парсер в `parser.py::_rule_based_parse`).

Настройка — в `nlp/.env` (см. `nlp/.env.example`) и в корневом `.env` (для backend через docker-compose).

### Выбор модели (обоснование — реальный бенчмарк, не предположение)

Прогнал 6 моделей RouterAI на реальных промптах проекта (парсинг QuerySpec, синтез, экстракция) —
результаты в `nlp/router_ai_benchmark.json`, `nlp/extraction_vs_yandex_results.json`,
`nlp/extraction_chunked_results.json`. Вывод:

| Задача | Где выполняется | Что важнее | Модель |
|---|---|---|---|
| Query parsing (QuerySpec) | Живой путь, SLA 3-5с (docs/ARCHITECTURE.md) | Скорость | `google/gemini-3.1-flash-lite` |
| Synthesis (ответ пользователю) | Тот же живой путь, тот же SLA-бюджет | Скорость | `google/gemini-3.1-flash-lite` |
| Extraction (ingestion) | Фоновый воркер, задержка не видна юзеру | Полнота графа | `qwen/qwen3-30b-a3b-instruct-2507` |

`qwen3.7-plus` — reasoning-модель, жрёт скрытые токены, 41с/вопрос — непригодна для живого пути.
`deepseek-v4-flash` — ломает JSON. `gemini-3-flash-preview` (дороже non-lite) — сжигает весь
токен-бюджет на рассуждения и не успевает выдать ответ. Дороже ≠ лучше для этой задачи.

## ML-1: Ingestion (документ → граф)

**Основной скрипт: `nlp/run_corpus_test.py`.**

```
parse (PyMuPDF) → chunk (recursive_split, без langchain) → extract (LLM + response_format)
→ normalize (term_aliases) → merge dedup → verify_measurements → write (Neo4j + Qdrant)
```

- **Chunking без `langchain_text_splitters`** — эта библиотека даёт **segfault на Python 3.14**
  (тот же класс проблемы, что у GLiNER/onnxruntime, см. `extraction_gliner.py`). Вместо неё —
  `recursive_split()` в `nlp/benchmark_extraction_chunked.py`, тот же алгоритм (рекурсивное
  разбиение по `\n\n`/`\n`/`.`/` `), без сегфолта.
- **Structured output** (`response_format` с JSON Schema, enum на `label`/`type`) — серверная
  grammar-constrained генерация (то же семейство техник, что Outlines/xgrammar, просто хостится
  провайдером, а не крутится локально). Подтверждено на реальных данных: убирает 100% случаев
  придуманных типов (`uses_process`, `Document`, `leads_to` — модель раньше их изобретала,
  несмотря на явный список в промпте).
- **`nlp/term_aliases.json` + `apply_term_aliases()`** — нормализация синонимов (шаг [5] Normalize
  из `docs/NLP_PIPELINE.md`). "ПВП"/"печь взвешенной плавки"/"fluidized bed furnace" схлопываются
  в один узел вместо трёх. Проверено тестом с синтетическим текстом, содержащим все три формы.
- **`verify_measurements()`** — механическая проверка: каждое число в узле `Measurement` должно
  буквально встречаться в исходном тексте документа. LLM иногда придумывает правдоподобные числа
  (реальный пример: модель написала "давление газа = 101325 Па", хотя в тексте вообще нет цифр
  про давление — 101325 Па это просто атмосферное давление, "правдоподобная константа").
  Промпт-инструкция "не выдумывай числа" снижает, но НЕ устраняет это полностью (сэмплинг даже
  при `temperature=0.1`) — механическая проверка нужна как страховка, не полагайтесь только на промпт.
  Непровеленные `Measurement` помечаются `properties.verified: false`, а не удаляются молча —
  чтобы можно было проверить руками.
- **Провенанс**: `Source`/`has_source` (страница документа) + `confidence` на `Finding` + `geography`
  (RU/foreign) на `Publication` — добавлено сверх оригинального `NER_pipeline_text_only.py`,
  которого не было даже в документированной онтологии до этой сессии.

### Запуск

```bash
# .env с ROUTERAI_API_KEY должен быть в nlp/.env
python nlp/run_corpus_test.py path/to/doc1.pdf path/to/doc2.pdf

# записать результат в реальный Neo4j/Qdrant (нужен docker compose up neo4j qdrant)
python -m nlp.ingestion.neo4j_import nlp/corpus_test_results/*_graph.json
python -m nlp.ingestion.qdrant_upload nlp/corpus_test_results/*_graph.json
```

### Известные ограничения ML-1

- **Language detection не реализован** (`fasttext-langdetect` из `docs/NLP_PIPELINE.md` не подключён).
- **`pint`-нормализация единиц не реализована** (мг/дм³ → мг/л делается только промптом, без библиотеки).
- **Entity resolution** ловит только точные дубли (регистр/пробелы) и известные алиасы из
  `term_aliases.json` — общей fuzzy/транслитерационной дедупликации нет (пример остаточной
  проблемы: email вида `IvanovII@company.ru` иногда всё ещё попадает отдельным узлом `Expert`
  вместо свойства существующего узла).
- Каталог экспериментов / справочники / список сотрудников из "Дополнительных материалов" ТЗ —
  **в реально выданном корпусе таких файлов нет** (проверено по содержимому всего zip-архива
  задачи — только `Источники информации/{Доклады,Журналы,Материалы конференций}`).

## ML-2: Query (вопрос → ответ)

**Модули: `nlp/query/parser.py`, `nlp/query/retrieval/*`, `nlp/synthesis/*`.**

```
parse (QuerySpecParser) → retrieve (HybridRetrievalEngine: Qdrant + Neo4j + RRF)
→ synthesize (SynthesisEngine) → subgraph (Neo4jClient.get_subgraph)
```

⚠️ Два похожих модуля синтеза существуют по историческим причинам:
`nlp/synthesis/engine.py` — тот, который реально подключён к backend
(`backend/src/app/infrastructure/providers/synthesis.py`). `nlp/query/retrieval/synthesis.py` —
более старая версия, оставлена для обратной совместимости с `nlp/query/retrieval/pipeline.py`,
но backend её не использует. При изменении логики синтеза правьте `nlp/synthesis/engine.py`.

### Баги, найденные и исправленные прогоном против реального Neo4j+Qdrant

Раньше эти модули были протестированы только по отдельности/с моками — против настоящих данных
гибридный поиск падал бы или молча возвращал пусто:

1. `neo4j_client.py` матчил по `n.canonical_name` — граф пишется с `n.id` (см. `neo4j_import.py`).
2. Cypher использовал типы связей `uses_material` (строчными) — в базе они `USES_MATERIAL`
   (Cypher регистрозависим).
3. `qdrant_upload.py` писал payload `entity_id`/`source_document`, `qdrant_client.py` читал
   `entity_ids`/`doc_id` — разные имена полей на записи и на чтении.
4. `qdrant_client.search()` не существует в установленной версии `qdrant-client` (1.18.0 клиент
   vs 1.12.4 сервер) — метод переименован в `query_points()`.
5. RRF-merge (`_reciprocal_rank_fusion` в `engine.py`) выбрасывал все метаданные (title/year/
   geography/confidence/span/extracted_at) кандидата, оставляя только `id`+`score` — синтез
   получал факты без единой цитаты для ответа.
6. **Числовые ограничения не матчились вообще** (проверено на ТЗ-примере "концентрации сульфатов
   <200 мг/л"): (а) модель иногда пишет буквальный `<`/`>` вместо разрешённых `<=`/`>=`/`=`,
   схема падала `ValidationError`, весь `numeric_constraint` терялся через откат на rule-based
   fallback (который не извлекает числа вообще) — исправлено мягким приведением `<`→`<=`;
   (б) Cypher в ОБЕИХ реализациях сравнивал имя свойства с `meas.id`/`meas.property`, а оно
   реально лежит на отдельном узле `Property` через `MEASURES_PROPERTY` — фильтр никогда ни с
   чем не совпадал. Проверено синтетическим тестом (150/250 мг/л при `<=200`): до фикса — 0
   результатов, после — корректно 1 из 2.

### Верификация знаний (`SourceCitation`, `docs/case-specification.md`: "источник, достоверность, дата актуализации")

- `year` — дата источника (год публикации).
- `extracted_at` — **другая** дата: когда факт был извлечён/обновлён в графе (`n.ingestion_date`
  из `neo4j_import.py`). Обе даты нужны по ТЗ, не путайте их.
- `confidence` — `high/medium/low`, на `Finding` проставляется LLM при экстракции.

### Межисточниковые противоречия (`disagreements`)

Не путать с `contradicts`-рёбрами, которые LLM ставит **внутри одного документа** при экстракции.
`disagreements` в ответе синтеза — это когда среди **разных retrieved источников** есть конфликт
(разные значения одного параметра, взаимоисключающие выводы). Механизм — промпт-инструкция
`SYNTHESIS_SYSTEM` (`nlp/synthesis/prompts.py`), LLM сравнивает все переданные находки. Проверено
на синтетическом конфликте (два источника с разным % извлечения) — заполняется корректно. На 4
реальных документах корпуса естественных противоречий не нашлось (темы разные), так что пустой
`disagreements` там — ожидаемый результат, а не баг реализации.

### Рекомендации (`recommendations`, `docs/case-specification.md`: "Рекомендации")

Поле `SynthesisResponse.recommendations` — `similar_case` (похожие кейсы из смежных областей) и
`related_topic` (смежные темы для углублённого изучения). Эксперты/лаборатории — отдельное поле
`experts`, не дублируются в `recommendations`.

### Сравнительные запросы (РУ vs мировая практика, вариант А vs Б)

`intent=compare` и поле `compare` парсятся корректно (проверено на обоих сценариях), но `compare`
**нигде не используется дальше** — ни в Cypher, ни в Qdrant-фильтрах, ни в synthesis (нет отдельного
Cypher/Qdrant-условия и нет двухпроходного retrieval "факты по A" + "факты по Б"). Вся
"сравнительность" итогового ответа держится на том, что LLM в synthesis сама сопоставляет факты по
`geography`-тегам, которые видит в контексте (`format_findings()`). Работает, когда retrieval
случайно нашёл факты по обеим сторонам сравнения; проверено на реальном вопросе про РУ/зарубежные
стандарты сейсмического воздействия — в графе реально есть 21 такой стандарт с верными
RU/foreign-тегами, но retrieval их не нашёл (сработало ограничение exact-id матчинга ниже), и
система честно ответила "нет данных" вместо выдумывания. Безопасно (не галлюцинирует), но это не
то же самое, что "сравнение работает надёжно".

### Известные ограничения ML-2

- **Cypher graph-search матчит по точному `id`.** Если `QuerySpecParser` выдаёт перефразировку
  вместо канонического имени узла (например "плавка в печи Ванюкова" вместо точного id узла в
  графе), graph-ветка вернёт 0 строк, и вся выдача идёт только от Qdrant vector search —
  семантически работает, но graph-фильтрация (по materials/processes) в таком случае не участвует.
  Нет fuzzy/embedding-резолюции сущностей запроса против графа. Это же ограничение — корневая
  причина того, почему сравнительные запросы иногда не находят реально существующие данные (см. выше).
- **Gap-detection и дашборд-метрики теперь реализованы** (`nlp/query/retrieval/analytics.py`):
  покрытие по доменам, material×process×condition без Experiment, RU/foreign-only темы, зоны
  риска (мало источников, противоречия) — всё проверено против реального графа, плюс backend
  read-эндпоинт `GET /dashboard/summary` (`backend/src/app/features/dashboard/summary/`).
  Не путать с полем `gaps` в ответе синтеза (то — про нехватку данных в контексте конкретного
  запроса, а не про системные пробелы БЗ). Фронтенд-страница дашборда — не реализована, данные
  для неё уже готовы.
- **Language detect** (`nlp/lang_detect.py`, `langdetect` вместо `fasttext-langdetect` — тот же
  принцип замены, что и `recursive_split()` вместо `langchain_text_splitters`, но здесь ради
  экономии времени на скачивание модели, не из-за краша) и **`pint`-нормализация единиц**
  (`nlp/units.py`, конвертирует концентрации в канонический мг/л, проверено на примере из
  `docs/ONTOLOGY.md`) реализованы и подключены в `run_corpus_test.py`.

## Бенчмарк-скрипты (для воспроизводимости / доклада)

- `benchmark_router_ai.py` — сравнение моделей RouterAI на реальных промптах (parse/synthesis/extraction).
- `benchmark_extraction_vs_yandex.py` — апрель-к-апрелю сравнение старого YandexGPT-бейзлайна и RouterAI на том же документе.
- `benchmark_extraction_chunked.py` — то же самое, но с честным чанкингом (~1500 симв/чанк) вместо целого документа за раз; отсюда же взят `recursive_split()`.
- `benchmark_multimodal_timing.py` — сравнение по времени: только текст vs текст + vision-описания картинок (PyMuPDF рендер страницы → vision-модель → текст в промпт).
- `test_structured_output.py` — сравнение с/без `response_format` на тех же чанках, что падали без него.
- `run_corpus_test.py` — основной прогон на реальных документах кейса (см. выше).

## Устаревшие/параллельные скрипты

- `NER_pipeline_text_only.py`, `NER_pipeline_multimodal_aug.py` — более ранние версии ingestion,
  жёстко завязаны на YandexGPT (`API_KEY`/`FOLDER_ID` в коде, не через `.env`), не переключены на
  RouterAI. `run_corpus_test.py` — актуальная версия с провайдер-независимой конфигурацией.
- `llm_ner_extract.py` — демо-скрипт извлечения, использует `QuerySpecParser.complete()` (общий
  провайдер-агностик метод), но старую (`EXTRACTION_SCHEMA.md`) схему `entities/measurements/
  relations/findings`, а не `nodes/edges`-формат, который реально пишется в Neo4j
  (`neo4j_import.py` ожидает именно `nodes/edges`, см. `EXTRACTION_SCHEMA.md` про две
  параллельные схемы контракта).
