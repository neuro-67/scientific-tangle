import { Navigate } from "react-router-dom";

import { useAuth } from "@/entities/session";
import { ROUTES } from "@/shared/constants";

import { LoginForm } from "./login-form";

/** Centered login screen. Redirects away if already authenticated. */
export function LoginPage() {
  const { isAuthenticated } = useAuth();

  if (isAuthenticated) {
    return <Navigate to={ROUTES.search} replace />;
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <LoginForm />
    </div>
  );
}
