import { API } from "@/shared/lib/axios";

import type { User } from "../model/session.types";

export type Req = {
  email: string;
  password: string;
};

type Res = {
  access_token: string;
  user: User;
};

/** POST /auth/login — exchange credentials for a JWT + user profile. */
export const login = (body: Req) =>
  API.post<Res>("/auth/login", body).then((r) => r.data);
