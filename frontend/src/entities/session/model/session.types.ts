/** RBAC roles from the backend brief (app.domain.entities.user.UserRole). */
export type UserRole =
  | "admin"
  | "project_manager"
  | "analyst"
  | "researcher"
  | "external_partner";

/**
 * Frontend user projection. `email` carries the backend `username` and `name`
 * carries `full_name` — kept as `email`/`name` so the existing UI stays stable.
 */
export type User = {
  id: string;
  email: string;
  name: string;
  role: UserRole;
};
