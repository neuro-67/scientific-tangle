import { API } from "@/shared/lib/axios";

export type GraphNodeDto = {
  id: string;
  label: string;
  type: string;
};

export type GraphEdgeDto = {
  id: string;
  source: string;
  target: string;
  type: string;
  label: string | null;
};

export type CreateNodeBody = {
  type: string;
  label: string;
  properties?: Record<string, unknown>;
};

export type UpdateNodeBody = {
  label?: string;
  properties?: Record<string, unknown>;
};

export type CreateEdgeBody = {
  source: string;
  target: string;
  type: string;
  label?: string;
};

export type UpdateEdgeBody = {
  label?: string;
};

export const createGraphNode = (body: CreateNodeBody) =>
  API.post<GraphNodeDto>("/graph/nodes", body).then((r) => r.data);

export const updateGraphNode = (id: string, body: UpdateNodeBody) =>
  API.patch<GraphNodeDto>(`/graph/nodes/${encodeURIComponent(id)}`, body).then(
    (r) => r.data
  );

export const deleteGraphNode = (id: string) =>
  API.delete<void>(`/graph/nodes/${encodeURIComponent(id)}`).then((r) => r.data);

export const createGraphEdge = (body: CreateEdgeBody) =>
  API.post<GraphEdgeDto>("/graph/edges", body).then((r) => r.data);

export const updateGraphEdge = (id: string, body: UpdateEdgeBody) =>
  API.patch<GraphEdgeDto>(`/graph/edges/${encodeURIComponent(id)}`, body).then(
    (r) => r.data
  );

export const deleteGraphEdge = (id: string) =>
  API.delete<void>(`/graph/edges/${encodeURIComponent(id)}`).then((r) => r.data);
