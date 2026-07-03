import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import type { ReactNode } from "react";

import { Toaster } from "@/shared/ui";

import { queryClient } from "./query-client";

type Props = {
  children: ReactNode;
};

/** Composes global providers (query cache, toasts, devtools). */
export function AppProvider({ children }: Props) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster position="top-right" richColors />
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
