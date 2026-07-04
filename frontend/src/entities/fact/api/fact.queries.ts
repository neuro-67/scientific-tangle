import { queryOptions } from "@tanstack/react-query";

import { getFactHistory, type Req as GetFactHistoryReq } from "./get-fact-history";

export const queries = {
  all: () => ["fact"] as const,
  history: ({ factId }: GetFactHistoryReq) =>
    queryOptions({
      queryKey: [...queries.all(), "history", factId],
      queryFn: () => getFactHistory({ factId }),
      enabled: Boolean(factId),
    }),
};
