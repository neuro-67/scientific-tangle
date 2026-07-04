import { createBrowserRouter } from "react-router-dom";

import { AnswerPage } from "@/pages/answer";
import { HistoryPage } from "@/pages/history";
import { LoginPage } from "@/pages/login";
import { NotFoundPage } from "@/pages/not-found";
import { SearchPage } from "@/pages/search";
import { ROUTES } from "@/shared/constants";

import { AppLayout } from "../layout/app-layout";
import { RequireAuth } from "./guards/require-auth";

export const router = createBrowserRouter([
  { path: ROUTES.login, element: <LoginPage /> },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { path: ROUTES.search, element: <SearchPage /> },
          { path: ROUTES.answer, element: <AnswerPage /> },
          { path: ROUTES.history, element: <HistoryPage /> },
          { path: ROUTES.notFound, element: <NotFoundPage /> },
        ],
      },
    ],
  },
]);
