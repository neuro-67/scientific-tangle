import { API } from "@/shared/lib/axios";

export type Req = {
  username: string;
  password: string;
};

/**
 * Body returned by the backend — the JWTs live in httpOnly cookies, so the
 * response only reports when they expire.
 */
type Res = {
  access_expires_at: string;
  refresh_expires_at: string;
};

/** POST /auth/login — exchange credentials for auth cookies (Set-Cookie). */
export const login = (body: Req) =>
  API.post<Res>("/auth/login", body).then((r) => r.data);
