import { RouterProvider } from "react-router-dom";

import { AppProvider } from "./providers/app-provider";
import { router } from "./router/router";
import "./styles/index.css";

export function App() {
  return (
    <AppProvider>
      <RouterProvider router={router} />
    </AppProvider>
  );
}
