import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "@/entities/session";
import { ROUTES } from "@/shared/constants";

/** Blocks routes for unauthenticated users; remembers the intended location. */
export function RequireAuth() {
  const location = useLocation();
  const { isAuthenticated, isLoadingUser } = useAuth();

  // Wait for GET /auth/me to resolve before deciding — the auth cookie is
  // httpOnly, so we can't know synchronously whether the user is logged in.
  if (isLoadingUser) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">
        Загрузка…
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <Navigate to={ROUTES.login} replace state={{ from: location.pathname }} />
    );
  }

  return <Outlet />;
}
