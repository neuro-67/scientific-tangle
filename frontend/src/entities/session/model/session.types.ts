/** RBAC roles from the project spec (see docs/ROADMAP.md). */
export type UserRole = "researcher" | "expert" | "manager" | "admin" | "guest";

export type User = {
  id: string;
  email: string;
  name: string;
  role: UserRole;
};
