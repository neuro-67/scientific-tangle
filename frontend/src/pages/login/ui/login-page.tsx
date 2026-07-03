import { Navigate } from "react-router-dom";

import { ROUTES } from "@/shared/constants";
import { getAccessToken } from "@/shared/lib/axios";

import { LoginForm } from "./login-form";

/** Centered login screen. Redirects away if already authenticated. */
export function LoginPage() {
  if (getAccessToken()) {
    return <Navigate to={ROUTES.search} replace />;
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <LoginForm />
    </div>
  );
}
