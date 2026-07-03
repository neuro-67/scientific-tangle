import { API } from "@/shared/lib/axios";
import type { ConfidenceLevel, Geography } from "@/shared/types";

import type { QueryAnswer } from "../model/query.types";

export type Req = {
  question: string;
  materials?: string[];
  processes?: string[];
  geography?: Geography;
  year_from?: number;
  year_to?: number;
  /** Minimum confidence level of returned sources. */
  confidence?: ConfidenceLevel;
};

type Res = QueryAnswer;

/** POST /query — orchestrates retrieval + synthesis, returns a cited answer. */
export const postQuery = (body: Req) =>
  API.post<Res>("/query", body).then((r) => r.data);
