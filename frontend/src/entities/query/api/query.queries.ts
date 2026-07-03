import { queryOptions } from "@tanstack/react-query";

import { postQuery, type Req as PostQueryReq } from "./post-query";

/**
 * TanStack Query factory for the query domain.
 * Used with `useQuery` for GET-style reads; the search flow itself issues the
 * question through this factory once a question is present.
 */
export const queries = {
  all: () => ["query"] as const,
  ask: (body: PostQueryReq) =>
    queryOptions({
      queryKey: [...queries.all(), "ask", body],
      queryFn: () => postQuery(body),
      enabled: body.question.trim().length > 0,
    }),
};
