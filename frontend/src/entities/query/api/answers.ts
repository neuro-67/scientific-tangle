import { API } from "@/shared/lib/axios";

import type {
  CreateEdgeBody,
  CreateNodeBody,
  GraphEdgeDto,
  GraphNodeDto,
  UpdateEdgeBody,
  UpdateNodeBody,
} from "@/entities/graph";

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

// Answer-scoped graph mutations. These write to Neo4j via the graph repo and
// patch the answer's stored subgraph snapshot in one shot, so edits (including
// orphan nodes like comments) persist across a page refresh.

export const createAnswerNode = (answerId: string, body: CreateNodeBody) =>
  API.post<GraphNodeDto>(`/answers/${answerId}/nodes`, body).then((r) => r.data);

export const updateAnswerNode = (
  answerId: string,
  nodeId: string,
  body: UpdateNodeBody
) =>
  API.patch<GraphNodeDto>(
    `/answers/${answerId}/nodes/${encodeURIComponent(nodeId)}`,
    body
  ).then((r) => r.data);

export const deleteAnswerNode = (answerId: string, nodeId: string) =>
  API.delete<void>(
    `/answers/${answerId}/nodes/${encodeURIComponent(nodeId)}`
  ).then((r) => r.data);

export const createAnswerEdge = (answerId: string, body: CreateEdgeBody) =>
  API.post<GraphEdgeDto>(`/answers/${answerId}/edges`, body).then((r) => r.data);

export const updateAnswerEdge = (
  answerId: string,
  edgeId: string,
  body: UpdateEdgeBody
) =>
  API.patch<GraphEdgeDto>(
    `/answers/${answerId}/edges/${encodeURIComponent(edgeId)}`,
    body
  ).then((r) => r.data);

export const deleteAnswerEdge = (answerId: string, edgeId: string) =>
  API.delete<void>(
    `/answers/${answerId}/edges/${encodeURIComponent(edgeId)}`
  ).then((r) => r.data);
