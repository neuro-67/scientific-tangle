import type { ConfidenceLevel } from "@/shared/types";
import type { AnswerSource, PostQueryReq, QueryAnswer } from "@/entities/query";

// Higher rank = more trustworthy; used to apply the "minimum confidence" filter.
const CONFIDENCE_RANK: Record<ConfidenceLevel, number> = {
  low: 0,
  medium: 1,
  high: 2,
};

/**
 * Builds a rich, demo-friendly answer for the mock backend. The response echoes
 * the incoming filters so the UI visibly reacts to what the user selected.
 */
export function buildMockAnswer(req: PostQueryReq): QueryAnswer {
  const geo = req.geography ?? "any";
  const materials = req.materials ?? ["сульфаты", "хлориды"];
  const processes = req.processes ?? ["обессоливание"];
  const minConfidence = req.confidence ? CONFIDENCE_RANK[req.confidence] : 0;

  const yearFrom = req.date_from
    ? new Date(req.date_from).getFullYear()
    : undefined;
  const yearTo = req.date_to ? new Date(req.date_to).getFullYear() : undefined;

  const allSources: AnswerSource[] = [
    {
      title: "Технологический отчёт по обессоливанию пластовых вод",
      year: 2023,
      geography: "RU",
      confidence: "high",
      span: "p.42",
    },
    {
      title: "Membrane desalination of high-salinity brines",
      year: 2021,
      geography: "foreign",
      confidence: "medium",
      span: "p.7",
    },
    {
      title: "Каталог экспериментов: циркуляция католита",
      year: 2024,
      geography: "RU",
      confidence: "low",
      span: "row 118",
    },
  ];

  return {
    answer:
      `По запросу «${req.question}» найдено согласованное подмножество источников. ` +
      `Для процессов ${processes.join(", ")} и материалов ${materials.join(", ")} ` +
      `оптимальные режимы подтверждаются экспериментальными данными. ` +
      `Отбор источников учитывает географию, год публикации и уровень достоверности. ` +
      `Это мок-ответ: контракт совпадает с будущим POST /query.`,
    consensus: [
      "Обратный осмос эффективен при сухом остатке ≤ 1000 мг/л.",
      "Предочистка от взвесей обязательна для стабильной работы мембран.",
    ],
    disagreements: [
      {
        point: "Целевой порог по сульфатам",
        sources_a: ["Отчёт ГМК, 2023"],
        sources_b: ["Zhang et al., 2021"],
      },
    ],
    sources: allSources.filter(
      (s) =>
        (geo === "any" || s.geography === geo) &&
        CONFIDENCE_RANK[s.confidence] >= minConfidence &&
        (yearFrom === undefined || s.year >= yearFrom) &&
        (yearTo === undefined || s.year <= yearTo)
    ),
    gaps: [
      "Нет экспериментов: холодный климат + кучное выщелачивание + Ni-руда.",
    ],
    experts: [
      { name: "И. Петров", affiliation: "R&D центр, гидрометаллургия" },
    ],
    laboratories: [
      { name: "Лаборатория мембранных технологий", institution: "ИГД УрО РАН" },
    ],
    confidence: "medium",
    subgraph: {
      nodes: [
        { id: "m1", label: materials[0] ?? "сульфаты", type: "Material" },
        { id: "p1", label: processes[0] ?? "обессоливание", type: "Process" },
        { id: "e1", label: "обратный осмос", type: "Equipment" },
        { id: "r1", label: "сухой остаток ≤ 1000 мг/л", type: "Result" },
      ],
      edges: [
        {
          id: "e1-1",
          source: "m1",
          target: "p1",
          type: "applies_to",
          label: "применяется к",
        },
        {
          id: "e1-2",
          source: "p1",
          target: "e1",
          type: "uses_equipment",
          label: "использует",
        },
        {
          id: "e1-3",
          source: "e1",
          target: "r1",
          type: "produces_output",
          label: "производит",
        },
      ],
    },
    spec: {
      intent: "review",
      materials,
      processes,
      geography: geo,
      time_range: yearFrom || yearTo ? { from: yearFrom, to: yearTo } : null,
      numeric_constraints: [],
      compare: null,
    },
  };
}
