import { API } from "@/shared/lib/axios";
import type { Geography } from "@/shared/types";

import type { QueryAnswer } from "../model/query.types";

export type Req = {
  question: string;
  geography?: Geography;
  year_from?: number;
  year_to?: number;
};

type Res = QueryAnswer;

/** POST /query — orchestrates retrieval + synthesis, returns a cited answer. */
export const postQuery = (body: Req) =>
  API.post<Res>("/query", body).then((r) => r.data);
