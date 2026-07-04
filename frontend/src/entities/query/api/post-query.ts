import { API } from "@/shared/lib/axios";
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

export type Req = {
  question: string;
  materials?: string[];
  processes?: string[];
  geography?: Geography;
  /** Publication date range in ISO format (YYYY-MM-DD). */
  date_from?: string;
  date_to?: string;
  /** Minimum confidence level of returned sources. */
  confidence?: ConfidenceLevel;
};

/** Number of retrieval candidates the backend reranks + synthesizes over. */
const DEFAULT_TOP_K = 10;

/**
 * Raw response from POST /query/ask (app.features.query.ask.schemas).
 * The backend nests the parsed spec and the synthesized answer; the UI wants a
 * single flat `QueryAnswer`, so `toQueryAnswer` below adapts it.
 */
type AskQuestionResponse = {
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

/** Extract a 4-digit year from an ISO date; the backend filters by year int. */
const yearOf = (iso?: string): number | undefined => {
  if (!iso) return undefined;
  const year = Number(iso.slice(0, 4));
  return Number.isFinite(year) && year > 0 ? year : undefined;
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

const toSubgraph = (
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

/** Flatten the backend's {query_spec, synthesis} envelope into a QueryAnswer. */
const toQueryAnswer = (res: AskQuestionResponse): QueryAnswer => {
  const { synthesis } = res;
  return {
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

/** POST /query/ask — parse + hybrid retrieval + synthesis → cited answer. */
export const postQuery = (body: Req) =>
  API.post<AskQuestionResponse>("/query/ask", {
    question: body.question,
    top_k: DEFAULT_TOP_K,
    materials: body.materials,
    processes: body.processes,
    geography: body.geography,
    year_from: yearOf(body.date_from),
    year_to: yearOf(body.date_to),
  }).then((r) => toQueryAnswer(r.data));
