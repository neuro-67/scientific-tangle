import axios from "axios";

import { env } from "@/shared/config/env";

/**
 * Shared axios instance. Every API file must import `API` from here and call
 * `API.get/post/patch/put/delete` directly (see docs/frontend/AGENTS.md).
 *
 * Auth uses httpOnly cookies set by the backend (`st_access` / `st_refresh`),
 * so there is no bearer token to attach — we just send credentials with every
 * request. `withCredentials` also makes the browser accept the Set-Cookie
 * response from `POST /auth/login`.
 */
export const API = axios.create({
  baseURL: env.apiBaseUrl,
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});
