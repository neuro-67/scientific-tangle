import { API } from "@/shared/lib/axios";

export type Req = {
  id: string;
};

/** DELETE /documents/{id} — cascade cleanup of blob, graph, and vectors. */
export const deleteDocument = ({ id }: Req) =>
  API.delete<void>(`/documents/${id}`).then((r) => r.data);
