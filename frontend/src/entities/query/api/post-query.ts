import { API } from "@/shared/lib/axios";
import type { ConfidenceLevel, Geography } from "@/shared/types";

import { toQueryAnswer, type AskQuestionResponse } from "./post-query.helpers";

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

/** Extract a 4-digit year from an ISO date; the backend filters by year int. */
const yearOf = (iso?: string): number | undefined => {
  if (!iso) return undefined;
  const year = Number(iso.slice(0, 4));
  return Number.isFinite(year) && year > 0 ? year : undefined;
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
