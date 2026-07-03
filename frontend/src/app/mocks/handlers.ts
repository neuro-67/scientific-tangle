import { delay, http, HttpResponse } from "msw";

import type { PostQueryReq } from "@/entities/query";
import type { LoginReq, User, UserRole } from "@/entities/session";
import { env } from "@/shared/config/env";

const base = env.apiBaseUrl;

const roleForEmail = (email: string): UserRole => {
  if (email.includes("admin")) return "admin";
  if (email.includes("manager") || email.includes("boss")) return "manager";
  if (email.includes("expert")) return "expert";
  if (email.includes("guest")) return "guest";
  return "researcher";
};

const makeUser = (email: string): User => ({
  id: email,
  email,
  name: email.split("@")[0] || email,
  role: roleForEmail(email),
});

// Token that carries the user payload so GET /auth/me works after a reload.
const encodeToken = (user: User) =>
  `mock.${btoa(unescape(encodeURIComponent(JSON.stringify(user))))}`;

const decodeToken = (token: string): User | null => {
  if (!token.startsWith("mock.")) return null;
  try {
    return JSON.parse(decodeURIComponent(escape(atob(token.slice(5)))));
  } catch {
    return null;
  }
};

export const handlers = [
  http.post(`${base}/auth/login`, async ({ request }) => {
    const { email, password } = (await request.json()) as LoginReq;
    if (!email || !password) {
      return HttpResponse.json(
        { detail: "Введите email и пароль" },
        { status: 401 }
      );
    }
    await delay(300);
    const user = makeUser(email);
    return HttpResponse.json({ access_token: encodeToken(user), user });
  }),

  http.get(`${base}/auth/me`, ({ request }) => {
    const token = request.headers.get("Authorization")?.replace("Bearer ", "");
    const user = token ? decodeToken(token) : null;
    if (!user) {
      return HttpResponse.json({ detail: "Не авторизован" }, { status: 401 });
    }
    return HttpResponse.json(user);
  }),

  http.post(`${base}/query`, async ({ request }) => {
    const body = (await request.json()) as PostQueryReq;
    await delay(700);
    const { buildMockAnswer } = await import("./mock-answer");
    return HttpResponse.json(buildMockAnswer(body));
  }),
];
