import { QueryClient } from "@tanstack/react-query";

/** App-wide TanStack Query client with demo-friendly defaults. */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});
