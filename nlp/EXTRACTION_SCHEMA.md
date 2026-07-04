# Контракт извлечения и QuerySpec

Этот документ — интерфейс между ML-1 (Ingestion) и ML-2 (Query/Retrieval).
Любые изменения согласовываются обеими сторонами и Backend.

## A. Extraction schema (Ingestion, ML-1)

Каждый чанк документа превращается LLM/NER в следующий JSON:

```json
{
  "entities": [
    {
      "type": "Material",
      "surface": "католит",
      "canonical": "католит",
      "attrs": {}
    }
  ],
  "measurements": [
    {
      "property": "сульфаты",
      "operator": "<=",
      "value": 300,
      "min": null,
      "max": null,
      "unit": "мг/л",
      "applies_to_surface": "исходная вода"
    }
  ],
  "conditions": [
    {"name": "климат", "value": "холодный"}
  ],
  "relations": [
    {
      "head": "электроэкстракция",
      "head_type": "Process",
      "type": "uses_material",
      "tail": "католит",
      "tail_type": "Material",
      "evidence": "...цитата..."
    }
  ],
  "findings": [
    {
      "statement": "оптимальная скорость циркуляции католита 0.8–1.2 м/с",
      "confidence": "medium"
    }
  ]
}
```

### Правила

1. `canonical` — ключ узла в графе. Должен быть стабильным и каноническим.
2. `surface` — оригинальный текст (для провенанса).
3. `evidence` обязателен для каждой связи.
4. Числа структурны: `operator`, `value`, `min`, `max`, `unit`.
5. Единицы канонизируются (`мг/дм³` → `мг/л`).
6. Если данных нет — пустой массив, не `null`.

### Типы сущностей (онтология)

| Type | Описание | Пример canonical |
|---|---|---|
| `Material` | Вещества, материалы | `католит`, `сульфаты` |
| `Process` | Технологические процессы | `электроэкстракция`, `обессоливание` |
| `Equipment` | Оборудование | `фильтр-пресс` |
| `Property` | Параметр | `концентрация`, `скорость` |
| `Measurement` | Числовое значение | пишется отдельным блоком |
| `Condition` | Условие/режим | `холодный климат` |
| `Experiment` | Опыт/протокол | — |
| `Publication` | Публикация/отчёт/патент | — |
| `Expert` | Автор | `Иванов И.И.` |
| `Facility` | Лаборатория/предприятие | `НИТУ МИСИС` |
| `Finding` | Вывод/эффект | — |

### Типы связей

```text
uses_material          Process/Experiment → Material
applies_to             Process → Material
operates_at_condition  Process/Experiment → Condition
has_measurement        Process/Experiment/Property → Measurement
measures_property      Measurement → Property
uses_equipment         Process/Experiment → Equipment
produces_output        Process/Experiment → Material/Finding
showed                 Experiment → Finding
described_in           * → Publication
authored_by            Publication → Expert
expert_in              Expert → Topic/Process
conducted_at           Experiment → Facility
validated_by           Finding/Fact → Expert
contradicts            Finding → Finding
supports               Finding → Finding
tagged                 * → Topic
has_source             (факт) → Source
```

---

## B. QuerySpec schema (Query, ML-2)

Вопрос пользователя парсится в:

```json
{
  "intent": "review",
  "materials": ["сульфаты", "хлориды"],
  "processes": ["обессоливание"],
  "equipment": [],
  "geography": "any",
  "time_range": {"from": 2020, "to": 2025},
  "numeric_constraints": [
    {"property": "сульфаты", "operator": "range", "min": 200, "max": 300, "unit": "мг/л"},
    {"property": "сухой остаток", "operator": "<=", "value": 1000, "unit": "мг/л"}
  ],
  "compare": null
}
```

### Поля

| Поле | Тип | Описание |
|---|---|---|
| `intent` | enum | `search`, `review`, `compare`, `gap` |
| `materials` | list[str] | Канонические имена материалов |
| `processes` | list[str] | Канонические имена процессов |
| `equipment` | list[str] | Канонические имена оборудования |
| `geography` | enum | `RU`, `foreign`, `any` |
| `time_range` | object | `{from, to}` — годы публикаций |
| `numeric_constraints` | list | Числовые фильтры |
| `compare` | str/null | Второй объект для intent=compare |

### Согласование с extraction

- `materials`, `processes`, `equipment` в QuerySpec должны совпадать по `canonical` с `entities` из extraction.
- `numeric_constraints.property` совпадает с `measurements.property` и `Property.name`.
- Канонизация терминов выполняется через общий `term_aliases`.

---

## C. Как согласовывать изменения

1. Любое изменение схемы — PR с обновлением этого файла.
2. ML-1 и ML-2 проверяют, что их парсеры/писатели совместимы.
3. Backend проверяет, что его Pydantic-модели совпадают.
4. Тест: 4 золотых вопроса + 1 тестовый чанк проходят сквозь обе схемы.
