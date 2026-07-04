import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { sessionApi } from "@/entities/session";
import { ROUTES } from "@/shared/constants";
import { handleApiError } from "@/shared/lib/api-error";
import { Button, IconInput, Label } from "@/shared/ui";

type LocationState = { from?: string } | null;

/** Credentials form. On success the backend sets auth cookies and we redirect. */
export function LoginForm() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();

  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin");
  const [remember, setRemember] = useState(false);

  const loginMutation = useMutation({
    mutationFn: sessionApi.login,
    onSuccess: async () => {
      // Cookies are set by the response; refetch the user before navigating.
      await queryClient.invalidateQueries({
        queryKey: sessionApi.queries.all(),
      });
      const from = (location.state as LocationState)?.from;
      navigate(from ?? ROUTES.search, { replace: true });
    },
    onError: (error) => handleApiError(error, { fallback: "Не удалось войти" }),
  });

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    loginMutation.mutate({ username, password });
  };

  return (
    <form onSubmit={onSubmit} className="flex w-full max-w-md flex-col gap-5">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="username">Логин</Label>
        <IconInput
          id="username"
          type="text"
          icon="/assets/icon-user.png"
          placeholder="admin"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
          required
        />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="password">Пароль</Label>
        <IconInput
          id="password"
          type="password"
          icon="/assets/icon-lock.png"
          placeholder="••••••••"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          required
        />
      </div>

      <div className="flex items-center justify-between text-sm">
        <label className="flex cursor-pointer items-center gap-2 text-muted-foreground">
          <input
            type="checkbox"
            checked={remember}
            onChange={(e) => setRemember(e.target.checked)}
            className="h-4 w-4 rounded border-input text-primary focus:ring-primary"
          />
          Запомнить меня
        </label>
        <a
          href="#"
          className="font-medium text-primary hover:underline"
          onClick={(e) => e.preventDefault()}
        >
          Забыли пароль?
        </a>
      </div>

      <Button
        type="submit"
        disabled={loginMutation.isPending}
        className="mt-2 h-11 w-full rounded-xl text-base"
      >
        {loginMutation.isPending ? "Вход…" : "Войти"}
      </Button>
    </form>
  );
}
