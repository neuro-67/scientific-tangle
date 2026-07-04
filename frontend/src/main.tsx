import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./app";

async function bootstrap() {
  // Mock backend (MSW). Enabled in dev unless explicitly turned off.
  if (import.meta.env.DEV && import.meta.env.VITE_ENABLE_MOCKS !== "false") {
    const { enableMocks } = await import("./app/mocks/browser");
    await enableMocks();
  }

  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <App />
    </StrictMode>
  );
}

void bootstrap();
