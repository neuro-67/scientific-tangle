import { createBrowserRouter } from "react-router-dom";

import { AnswerPage } from "@/pages/answer";
import { NotFoundPage } from "@/pages/not-found";
import { SearchPage } from "@/pages/search";
import { ROUTES } from "@/shared/constants";

import { AppLayout } from "../layout/app-layout";

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { path: ROUTES.search, element: <SearchPage /> },
      { path: ROUTES.answer, element: <AnswerPage /> },
      { path: ROUTES.notFound, element: <NotFoundPage /> },
    ],
  },
]);
