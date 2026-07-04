import { API } from "@/shared/lib/axios";

import type { Document } from "../model/document.types";

export type Req = {
  id: string;
};

type Res = Document;

/** GET /documents/{id} — a document's metadata and current ingestion status. */
export const getDocument = ({ id }: Req) =>
  API.get<Res>(`/documents/${id}`).then((r) => r.data);
