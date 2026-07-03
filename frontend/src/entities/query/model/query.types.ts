import type { ConfidenceLevel, Geography } from "@/shared/types";

/**
 * Domain types for the Query pipeline. Shapes mirror the backend contracts
 * documented in docs/NLP_PIPELINE.md (QuerySpec + synthesized answer).
 */

export type QueryIntent = "search" | "review" | "compare" | "gap";

export type NumericConstraint = {
  property: string;
  operator: "range" | "<=" | ">=" | "<" | ">" | "=";
  value?: number;
  min?: number;
  max?: number;
  unit?: string;
};

/** Structured filters parsed from the natural-language question. */
export type QuerySpec = {
  intent: QueryIntent;
  materials: string[];
  processes: string[];
  geography: Geography;
  time_range: { from?: number; to?: number } | null;
  numeric_constraints: NumericConstraint[];
  compare: string | null;
};

export type AnswerSource = {
  title: string;
  year: number;
  geography: Geography;
  confidence: ConfidenceLevel;
  span: string;
};

export type Disagreement = {
  point: string;
  sources_a: string[];
  sources_b: string[];
};

export type Expert = {
  name: string;
  affiliation: string;
};

/** A node of the answer subgraph (material/process/equipment/result). */
export type GraphNode = {
  id: string;
  label: string;
  type: string;
};

/** An edge of the answer subgraph; `contradicts` edges are highlighted in UI. */
export type GraphEdge = {
  id: string;
  source: string;
  target: string;
  type: string;
};

export type AnswerSubgraph = {
  nodes: GraphNode[];
  edges: GraphEdge[];
};

/** Synthesized answer returned by POST /query. */
export type QueryAnswer = {
  answer: string;
  consensus: string[];
  disagreements: Disagreement[];
  sources: AnswerSource[];
  gaps: string[];
  experts: Expert[];
  confidence: ConfidenceLevel;
  subgraph: AnswerSubgraph;
  spec: QuerySpec;
};
