import { API } from "@/shared/lib/axios";

import type { User, UserRole } from "../model/session.types";

/** Raw shape returned by GET /auth/me (app.features.users.schemas.UserResponse). */
type UserResponse = {
  id: string;
  username: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

const toUser = (dto: UserResponse): User => ({
  id: dto.id,
  email: dto.username,
  name: dto.full_name || dto.username,
  role: dto.role,
});

/** GET /auth/me — resolve the current user from the auth cookie. */
export const getCurrentUser = () =>
  API.get<UserResponse>("/auth/me").then((r) => toUser(r.data));
