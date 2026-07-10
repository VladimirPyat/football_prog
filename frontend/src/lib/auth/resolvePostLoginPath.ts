import type { UserOut } from "@/types/api";

export function resolvePostLoginPath(user: Pick<UserOut, "role" | "is_temp_password">): string {
  if (user.is_temp_password) return "/change-password";
  switch (user.role) {
    case "USER":
      return "/profile";
    case "SUPERVISOR":
      return "/admin/settings/parameters";
    case "SUPPORT":
      return "/admin";
    default:
      return "/";
  }
}
