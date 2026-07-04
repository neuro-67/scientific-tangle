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

/** Filter form state on the search screen (before it becomes a request). */
export type QueryFilters = {
  question: string;
  materials: string[];
  processes: string[];
  geography: Geography;
  /** Publication date range in ISO format (YYYY-MM-DD). */
  dateFrom: string | null;
  dateTo: string | null;
  /** Minimum confidence level of returned sources; "any" = no filter. */
  confidence: ConfidenceLevel | "any";
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
  /** Publication year of the source; null when the source has no year. */
  year: number | null;
  geography: Geography;
  confidence: ConfidenceLevel;
  /** Page / offset reference; null when unavailable. */
  span: string | null;
  /** Ingestion/modification date (ISO), distinct from the source's year. */
  extracted_at?: string | null;
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

export type Laboratory = {
  name: string;
  institution: string;
};

/**
 * One row of a compare-intent answer's technology comparison table
 * (case-specification.md "Дополнительные пожелания"). Always exactly 4 rows
 * — эффективность, капитальные затраты, применимость в холодном климате,
 * экологические ограничения — with "нет данных" in a cell instead of the
 * row being omitted. Empty array for non-compare answers.
 */
export type ComparisonRow = {
  criterion: string;
  side_a: string;
  side_b: string;
};

/** A node of the answer subgraph (material/process/equipment/result). */
export type GraphNode = {
  id: string;
  label: string;
  type: string;
  revision_count?: number;
};

/** An edge of the answer subgraph; `contradicts` edges are highlighted in UI. */
export type GraphEdge = {
  id: string;
  source: string;
  target: string;
  type: string;
  label?: string;
};

export type AnswerSubgraph = {
  nodes: GraphNode[];
  edges: GraphEdge[];
};

/** Lightweight row from GET /answers — for the history list. */
export type AnswerListItem = {
  id: string;
  question: string;
  confidence: ConfidenceLevel | null;
  created_at: string;
  updated_at: string;
};

/** Full persisted answer row from GET /answers/{id}. */
export type AnswerRecord = {
  id: string;
  question: string;
  query_spec: unknown;
  synthesis: unknown;
  subgraph: unknown;
  confidence: ConfidenceLevel | null;
  created_at: string;
  updated_at: string;
};

/** Synthesized answer returned by POST /query. */
export type QueryAnswer = {
  /** Persisted answer id (present when the row was saved). */
  id?: string;
  answer: string;
  consensus: string[];
  disagreements: Disagreement[];
  sources: AnswerSource[];
  gaps: string[];
  experts: Expert[];
  laboratories: Laboratory[];
  comparison_table: ComparisonRow[];
  confidence: ConfidenceLevel;
  subgraph: AnswerSubgraph;
  spec: QuerySpec;
};
