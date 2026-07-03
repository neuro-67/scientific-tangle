import { queryOptions } from "@tanstack/react-query";

import { getCurrentUser } from "./get-current-user";

export const queries = {
  all: () => ["session"] as const,
  me: () =>
    queryOptions({
      queryKey: [...queries.all(), "me"],
      queryFn: getCurrentUser,
    }),
};
