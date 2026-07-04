import { queryOptions } from "@tanstack/react-query";

import { getDocument } from "./get-document";
import { listDocuments, type Req as ListDocumentsReq } from "./list-documents";

/**
 * TanStack Query factory for the document domain. `detail` polls a single
 * document's status; `list` polls the full corpus so the upload page can
 * reflect ingestion progress while the user stays on it.
 */
export const queries = {
  all: () => ["document"] as const,
  detail: (id: string) =>
    queryOptions({
      queryKey: [...queries.all(), "detail", id],
      queryFn: () => getDocument({ id }),
    }),
  list: (params: ListDocumentsReq = {}) =>
    queryOptions({
      queryKey: [...queries.all(), "list", params],
      queryFn: () => listDocuments(params),
    }),
};
