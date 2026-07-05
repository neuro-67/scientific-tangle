import type { ConfidenceLevel, Geography } from "@/shared/types";

import type {
  AnswerSource,
  AnswerSubgraph,
  ComparisonRow,
  Disagreement,
  Expert,
  GraphEdge,
  GraphNode,
  Laboratory,
  QueryAnswer,
  QuerySpec,
} from "../model/query.types";

/**
 * Raw response from POST /query/ask and POST /answers/{id}/regenerate — both
 * endpoints share the same envelope shape (backend AskQuestionResponse).
 */
export type AskQuestionResponse = {
  id?: string | null;
  question: string;
  query_spec: {
    intent?: QuerySpec["intent"];
    materials?: string[];
    processes?: string[];
    geography?: Geography;
    time_range?: {
      from?: number;
      to?: number;
      from_year?: number;
      to_year?: number;
    } | null;
    numeric_constraints?: QuerySpec["numeric_constraints"];
    compare?: string | null;
  };
  synthesis: {
    answer: string;
    consensus?: string[];
    disagreements?: Array<Partial<Disagreement>>;
    sources?: Array<Partial<AnswerSource>>;
    gaps?: string[];
    experts?: Array<Partial<Expert>>;
    laboratories?: Array<Partial<Laboratory>>;
    comparison_table?: Array<Partial<ComparisonRow>>;
    confidence?: ConfidenceLevel | null;
  };
  subgraph?: {
    nodes?: Array<Partial<GraphNode>>;
    edges?: Array<Partial<GraphEdge>>;
  } | null;
};

const toSpec = (raw: AskQuestionResponse["query_spec"]): QuerySpec => ({
  intent: raw.intent ?? "search",
  materials: raw.materials ?? [],
  processes: raw.processes ?? [],
  geography: raw.geography ?? "any",
  time_range: raw.time_range
    ? {
        from: raw.time_range.from ?? raw.time_range.from_year,
        to: raw.time_range.to ?? raw.time_range.to_year,
      }
    : null,
  numeric_constraints: raw.numeric_constraints ?? [],
  compare: raw.compare ?? null,
});

const toSource = (s: Partial<AnswerSource>): AnswerSource => ({
  title: s.title ?? "Источник",
  year: s.year ?? null,
  geography: s.geography ?? "any",
  confidence: s.confidence ?? "low",
  span: s.span ?? null,
  extracted_at: s.extracted_at ?? null,
});

const toDisagreement = (d: Partial<Disagreement>): Disagreement => ({
  point: d.point ?? "",
  sources_a: d.sources_a ?? [],
  sources_b: d.sources_b ?? [],
});

const toExpert = (e: Partial<Expert>): Expert => ({
  name: e.name ?? "",
  affiliation: e.affiliation ?? "",
});

/** Node types that represent a lab / facility in the answer subgraph. */
const FACILITY_TYPES = new Set(["Facility", "Laboratory"]);

/**
 * Laboratories shown on the answer screen. The synthesis payload has no
 * dedicated labs field, so surface the graph-grounded Facility nodes from the
 * answer subgraph (dedup by name), plus any labs the LLM happened to emit.
 */
const toLaboratories = (
  llm: Array<Partial<Laboratory>> | undefined,
  subgraph: AnswerSubgraph
): Laboratory[] => {
  const out: Laboratory[] = [];
  const seen = new Set<string>();
  const push = (name?: string, institution?: string) => {
    const n = (name ?? "").trim();
    if (!n || seen.has(n.toLowerCase())) return;
    seen.add(n.toLowerCase());
    out.push({ name: n, institution: (institution ?? "").trim() });
  };
  for (const node of subgraph.nodes) {
    if (FACILITY_TYPES.has(node.type)) push(node.label);
  }
  for (const l of llm ?? []) push(l.name, l.institution);
  return out;
};

const toComparisonRow = (c: Partial<ComparisonRow>): ComparisonRow => ({
  criterion: c.criterion ?? "",
  side_a: c.side_a ?? "нет данных",
  side_b: c.side_b ?? "нет данных",
});

export const toSubgraph = (
  raw: AskQuestionResponse["subgraph"]
): AnswerSubgraph => {
  if (!raw) return { nodes: [], edges: [] };
  const nodes: GraphNode[] = (raw.nodes ?? [])
    .filter((n): n is GraphNode => Boolean(n?.id))
    .map((n) => ({
      id: String(n.id),
      label: n.label ?? String(n.id),
      type: n.type ?? "Node",
      revision_count: n.revision_count ?? 0,
      source_document: n.source_document ?? null,
    }));
  const nodeIds = new Set(nodes.map((n) => n.id));
  const edges: GraphEdge[] = (raw.edges ?? [])
    .filter(
      (e): e is GraphEdge =>
        Boolean(e?.id) &&
        Boolean(e?.source) &&
        Boolean(e?.target) &&
        // Cytoscape throws on edges that reference missing nodes — drop them.
        nodeIds.has(String(e.source)) &&
        nodeIds.has(String(e.target))
    )
    .map((e) => ({
      id: String(e.id),
      source: String(e.source),
      target: String(e.target),
      type: e.type ?? "related",
      label: e.label ?? e.type ?? "",
    }));
  return { nodes, edges };
};

/** Flatten the backend's {query_spec, synthesis, subgraph} envelope into a QueryAnswer. */
export const toQueryAnswer = (res: AskQuestionResponse): QueryAnswer => {
  const { synthesis } = res;
  const subgraph = toSubgraph(res.subgraph);
  return {
    id: res.id ?? undefined,
    answer: synthesis.answer,
    consensus: synthesis.consensus ?? [],
    disagreements: (synthesis.disagreements ?? [])
      .map(toDisagreement)
      .filter((d) => d.point),
    sources: (synthesis.sources ?? []).map(toSource),
    gaps: synthesis.gaps ?? [],
    experts: (synthesis.experts ?? []).map(toExpert).filter((e) => e.name),
    laboratories: toLaboratories(synthesis.laboratories, subgraph),
    comparison_table: (synthesis.comparison_table ?? [])
      .map(toComparisonRow)
      .filter((c) => c.criterion),
    confidence: synthesis.confidence ?? "low",
    subgraph,
    spec: toSpec(res.query_spec),
  };
};
