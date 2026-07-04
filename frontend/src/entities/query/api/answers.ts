import { API } from "@/shared/lib/axios";

import type { AnswerListItem, AnswerRecord, QueryAnswer } from "../model/query.types";

import { toQueryAnswer, type AskQuestionResponse } from "./post-query.helpers";

export const listAnswers = ({
  limit = 50,
  offset = 0,
}: { limit?: number; offset?: number } = {}) =>
  API.get<AnswerListItem[]>("/answers", { params: { limit, offset } }).then(
    (r) => r.data
  );

export const getAnswer = (id: string) =>
  API.get<AnswerRecord>(`/answers/${id}`).then((r) => r.data);

export const deleteAnswer = (id: string) =>
  API.delete<void>(`/answers/${id}`).then((r) => r.data);

/**
 * POST /answers/{id}/regenerate — re-runs the pipeline against the saved
 * question and updates the row. The response mirrors POST /query/ask, so we
 * reuse the same adapter to flatten it into a QueryAnswer.
 */
export const regenerateAnswer = (id: string): Promise<QueryAnswer> =>
  API.post<AskQuestionResponse>(`/answers/${id}/regenerate`).then((r) =>
    toQueryAnswer(r.data)
  );
