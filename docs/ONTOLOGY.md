# Онтология предметной области «Научный клубок»

Схема графа знаний для горно-металлургического R&D. Реализуется в Neo4j (labels + свойства + связи), задокументирована в OWL/SHACL-стиле. Это контракт между NLP-извлечением, графом и запросами — менять согласованно.

---

## 1. Типы сущностей (node labels)

| Label | Описание | Ключевые свойства |
|---|---|---|
| `Material` | Вещества и материалы | `canonical_name`, `formula`, `aliases[]`, `category` (сульфат/хлорид/металл/отход…) |
| `Process` | Технологические процессы | `canonical_name`, `domain` (гидромет/пиромет/экология/переработка), `aliases[]` |
| `Equipment` | Оборудование и установки | `canonical_name`, `type`, `aliases[]` |
| `Property` | Свойство/параметр | `name` (концентрация/температура/скорость потока/CAPEX), `dimension` |
| `Measurement` | Конкретное числовое значение/диапазон | `value`, `min`, `max`, `unit`, `operator` (≤,≥,=,range) |
| `Condition` | Условие/режим | `name` (климат=холодный, режим=кучное выщелачивание) |
| `Experiment` | Опыт/протокол | `title`, `date`, `result_summary` |
| `Publication` | Публикация/отчёт/патент/диссертация | `title`, `year`, `type`, `doi`, `geography` (RU/foreign), `sensitivity` |
| `Expert` | Автор/носитель компетенции | `name`, `affiliation` |
| `Facility` | Лаборатория/предприятие | `name`, `location` |
| `Finding` | Вывод/эффект/рекомендация | `statement`, `confidence` |
| `Source` | Провенанс-обёртка факта | `doc_id`, `span`, `extracted_at` |
| `Topic` | Тег таксономии | `name`, `domain` |

> Расширяемость: новый тип (напр. `EconomicIndicator`) добавляется как новый label + extraction-схема + Cypher-констрейнт, без ломки существующего.

---

## 2. Связи (relationship types)

| Связь | От → К | Смысл |
|---|---|---|
| `uses_material` | Process/Experiment → Material | процесс/опыт использует материал |
| `applies_to` | Process → Material | метод применяется для материала |
| `operates_at_condition` | Process/Experiment → Condition | режим/условие |
| `has_measurement` | Process/Experiment/Property → Measurement | числовое значение |
| `measures_property` | Measurement → Property | что именно измерено |
| `uses_equipment` | Process/Experiment → Equipment | оборудование |
| `produces_output` | Process/Experiment → Material/Finding | результат |
| `showed` | Experiment → Finding | эксперимент показал эффект |
| `described_in` | * → Publication | где описано (провенанс) |
| `authored_by` | Publication → Expert | автор |
| `expert_in` | Expert → Topic/Process | область экспертизы |
| `conducted_at` | Experiment → Facility | где проведён |
| `validated_by` | Finding/Fact → Expert | верифицировано экспертом |
| `contradicts` | Finding → Finding | противоречие выводов |
| `supports` | Finding → Finding | подтверждает |
| `tagged` | * → Topic | тематический тег |
| `has_source` | (любой факт) → Source | провенанс-связь |

---

## 3. Модель провенанса и достоверности

Каждый значимый факт связан с `Source` и несёт:

```
confidence  ∈ {high, medium, low}
geography   ∈ {RU, foreign}
valid_from  : date
valid_to    : date | null     # null = актуально
extracted_at: datetime
validated_by: Expert?         # повышает confidence
sensitivity ∈ {public, internal, confidential}
```

**Версионирование фактов:** при обновлении вывода старый факт получает `valid_to = now`, создаётся новый узел `Finding` с `valid_from = now`. История не теряется — требование ТЗ.

---

## 4. Пример: как ложится реальный запрос

Запрос: *«методы обессоливания воды: сульфаты/хлориды/Ca/Mg/Na по 200–300 мг/л, сухой остаток ≤1000 мг/дм³»*

```
(:Process {canonical_name:"обратный осмос", domain:"экология"})
  -[:applies_to]-> (:Material {canonical_name:"шахтная вода"})
  -[:operates_at_condition]-> (:Condition {name:"обессоливание"})
  -[:has_measurement]-> (:Measurement {property:"сульфаты", max:300, unit:"мг/л"})
  -[:produces_output]-> (:Finding {statement:"сухой остаток ≤1000 мг/дм³"})
  -[:described_in]-> (:Publication {year:2024, geography:"foreign", type:"article"})
  -[:has_source]-> (:Source {doc_id:"...", span:"p.42"})
```

Числовое ограничение `≤300 мг/л` матчится Cypher-фильтром по `Measurement.max`/`min`/`operator` — точное сравнение диапазонов, без «галлюцинаций».

---

## 5. Индексы Neo4j (для SLA 3–5 c)

```cypher
CREATE CONSTRAINT material_key IF NOT EXISTS
  FOR (m:Material) REQUIRE m.canonical_name IS UNIQUE;
CREATE INDEX proc_domain IF NOT EXISTS FOR (p:Process) ON (p.domain);
CREATE INDEX pub_year IF NOT EXISTS FOR (p:Publication) ON (p.year);
CREATE INDEX pub_geo  IF NOT EXISTS FOR (p:Publication) ON (p.geography);
CREATE INDEX meas_val IF NOT EXISTS FOR (x:Measurement) ON (x.value);
CREATE FULLTEXT INDEX ft_names IF NOT EXISTS
  FOR (n:Material|Process|Equipment) ON EACH [n.canonical_name];
```

---

## 6. Канонизация терминов (`term_aliases`, Postgres)

| alias | canonical | type | lang |
|---|---|---|---|
| electrowinning | электроэкстракция | Process | en |
| ПВП | печь взвешенной плавки | Equipment | ru |
| fluidized bed furnace | печь взвешенной плавки | Equipment | en |
| католит | католит | Material | ru |
| МПГ | металлы платиновой группы | Material | ru |

Канонизация выполняется на шаге Normalize ingestion-пайплайна; `canonical_name` — ключ узла (см. [NLP_PIPELINE.md](./NLP_PIPELINE.md)).

---

## 7. Обнаружение пробелов (gap detection)

Пример Cypher: комбинации материал × процесс × условие без эксперимента.

```cypher
MATCH (m:Material), (p:Process), (c:Condition)
WHERE NOT EXISTS {
  MATCH (e:Experiment)-[:uses_material]->(m)
  MATCH (e)-[:operates_at_condition]->(c)
  MATCH (e)-[:produces_output|showed]->()
  WHERE (e)-[:uses_material]->(m) AND (e)-[]->(p)
}
RETURN m.canonical_name, p.canonical_name, c.name LIMIT 50;
```

«Только RU / только foreign»: сравнение множеств `geography` у публикаций, связанных с темой.
