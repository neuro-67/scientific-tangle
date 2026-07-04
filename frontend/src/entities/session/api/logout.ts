import { API } from "@/shared/lib/axios";

/** POST /auth/logout — clears the auth cookies. Idempotent. */
export const logout = () => API.post<void>("/auth/logout").then(() => undefined);
