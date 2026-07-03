import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { sessionApi } from "@/entities/session";
import { ROUTES } from "@/shared/constants";
import { handleApiError } from "@/shared/lib/api-error";
import { setAccessToken } from "@/shared/lib/axios";
import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
  Label,
} from "@/shared/ui";

type LocationState = { from?: string } | null;

/** Credentials form. On success stores the JWT and redirects. */
export function LoginForm() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();

  const [email, setEmail] = useState("researcher@nornickel.ru");
  const [password, setPassword] = useState("demo");

  const loginMutation = useMutation({
    mutationFn: sessionApi.login,
    onSuccess: async (data) => {
      setAccessToken(data.access_token);
      await queryClient.invalidateQueries({
        queryKey: sessionApi.queries.all(),
      });
      const from = (location.state as LocationState)?.from;
      navigate(from ?? ROUTES.search, { replace: true });
    },
    onError: (error) =>
      handleApiError(error, { fallback: "Не удалось войти" }),
  });

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    loginMutation.mutate({ email, password });
  };

  return (
    <Card className="w-full max-w-sm">
      <CardHeader>
        <CardTitle>Вход в «Научный клубок»</CardTitle>
        <CardDescription>
          Демо-режим: подойдут любые email и пароль.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="username"
              required
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="password">Пароль</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>
          <Button type="submit" disabled={loginMutation.isPending}>
            {loginMutation.isPending ? "Вход…" : "Войти"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
