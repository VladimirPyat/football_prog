import type { UserRole } from "@/types/api";

const ROLE_RANK: Record<UserRole, number> = {
  USER: 1,
  SUPERVISOR: 2,
  SUPPORT: 3,
};

export function hasMinRole(userRole: UserRole | null, required: UserRole): boolean {
  if (!userRole) return false;
  return ROLE_RANK[userRole] >= ROLE_RANK[required];
}

export function isSupervisorOrAbove(role: UserRole | null): boolean {
  return hasMinRole(role, "SUPERVISOR");
}
