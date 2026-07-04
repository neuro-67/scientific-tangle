import { API } from "@/shared/lib/axios";

import type { Document } from "../model/document.types";

export type Req = {
  limit?: number;
  offset?: number;
};

type Res = Document[];

/** GET /documents — paginated list of documents with ingestion status, newest first. */
export const listDocuments = ({ limit = 50, offset = 0 }: Req = {}) =>
  API.get<Res>("/documents", { params: { limit, offset } }).then((r) => r.data);
