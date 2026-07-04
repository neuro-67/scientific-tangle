import { Navigate } from "react-router-dom";

import { ROUTES } from "@/shared/constants";
import { getAccessToken } from "@/shared/lib/axios";
import { AppLogo } from "@/shared/ui";

import { LoginForm } from "./login-form";

/** Centered login screen. Redirects away if already authenticated. */
export function LoginPage() {
  if (getAccessToken()) {
    return <Navigate to={ROUTES.search} replace />;
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[url('/assets/FON1.png')] bg-cover bg-center p-6">
      <div className="relative z-10 grid w-full max-w-5xl items-center gap-12 rounded-3xl bg-white/70 p-8 shadow-2xl backdrop-blur-sm lg:grid-cols-2 lg:p-12">
        {/* Left: form */}
        <div className="flex flex-col gap-6">
          <div className="flex items-center gap-3">
            <AppLogo className="h-10 w-10" />
            <span className="text-lg font-semibold">Научный клубок</span>
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-foreground lg:text-4xl">
              Добро пожаловать!
            </h1>
            <p className="mt-2 text-muted-foreground">Войдите в свой аккаунт</p>
          </div>
          <LoginForm />
        </div>

        {/* Right: illustration */}
        <div className="relative hidden min-h-[420px] items-center justify-center rounded-2xl bg-gradient-to-br from-[#dbeafe] to-[#eff6ff] lg:flex">
          <img
            src="/assets/illustration-microscope.png"
            alt=""
            className="h-72 w-72 object-contain drop-shadow-xl"
          />
        </div>
      </div>
    </div>
  );
}
