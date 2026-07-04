import { API } from "@/shared/lib/axios";

import type { Document } from "../model/document.types";

export type Req = {
  file: File;
};

type Res = Document;

/**
 * POST /documents — upload a source file as multipart/form-data. The backend
 * stores it and queues ingestion, returning the document in `pending` status.
 * Content-Type is overridden so axios sends FormData with a proper boundary
 * instead of the instance default `application/json`.
 */
export const uploadDocument = ({ file }: Req) => {
  const form = new FormData();
  form.append("file", file);
  return API.post<Res>("/documents", form, {
    headers: { "Content-Type": "multipart/form-data" },
  }).then((r) => r.data);
};
