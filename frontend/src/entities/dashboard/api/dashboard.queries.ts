import { queryOptions } from "@tanstack/react-query";

import { getDashboardSummary } from "./get-dashboard-summary";

export const queries = {
  all: () => ["dashboard"] as const,
  summary: () =>
    queryOptions({
      queryKey: [...queries.all(), "summary"],
      queryFn: getDashboardSummary,
    }),
};
