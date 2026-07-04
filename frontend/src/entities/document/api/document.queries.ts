import { queryOptions } from "@tanstack/react-query";

import { getDocument } from "./get-document";

/**
 * TanStack Query factory for the document domain. `detail` is used to poll a
 * single document's ingestion status until it reaches a terminal state.
 */
export const queries = {
  all: () => ["document"] as const,
  detail: (id: string) =>
    queryOptions({
      queryKey: [...queries.all(), "detail", id],
      queryFn: () => getDocument({ id }),
    }),
};
