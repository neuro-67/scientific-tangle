import type { ConfidenceLevel, Geography } from "@/shared/types";

import type {
  AnswerSource,
  AnswerSubgraph,
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

const toLaboratory = (l: Partial<Laboratory>): Laboratory => ({
  name: l.name ?? "",
  institution: l.institution ?? "",
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
    laboratories: (synthesis.laboratories ?? [])
      .map(toLaboratory)
      .filter((l) => l.name),
    confidence: synthesis.confidence ?? "low",
    subgraph: toSubgraph(res.subgraph),
    spec: toSpec(res.query_spec),
  };
};
