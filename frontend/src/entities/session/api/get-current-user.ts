import { API } from "@/shared/lib/axios";

import type { User } from "../model/session.types";

type Res = User;

/** GET /auth/me — resolve the current user from the bearer token. */
export const getCurrentUser = () =>
  API.get<Res>("/auth/me").then((r) => r.data);
