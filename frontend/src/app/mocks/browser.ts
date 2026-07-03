import { setupWorker } from "msw/browser";

import { handlers } from "./handlers";

export const worker = setupWorker(...handlers);

/** Start the MSW mock backend. No-op'd in production builds via the caller. */
export const enableMocks = () =>
  worker.start({
    onUnhandledRequest: "bypass",
    quiet: true,
  });
