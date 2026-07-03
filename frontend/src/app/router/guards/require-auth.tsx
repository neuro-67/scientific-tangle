import { Navigate, Outlet, useLocation } from "react-router-dom";

import { ROUTES } from "@/shared/constants";
import { getAccessToken } from "@/shared/lib/axios";

/** Blocks routes for unauthenticated users; remembers the intended location. */
export function RequireAuth() {
  const location = useLocation();

  if (!getAccessToken()) {
    return (
      <Navigate to={ROUTES.login} replace state={{ from: location.pathname }} />
    );
  }

  return <Outlet />;
}
