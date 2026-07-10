import { describe, it, expect } from "vitest";
import { resolvePostLoginPath } from "@/lib/auth/resolvePostLoginPath";

describe("resolvePostLoginPath", () => {
  it("redirects temp password users to change-password", () => {
    expect(resolvePostLoginPath({ role: "USER", is_temp_password: true })).toBe("/change-password");
    expect(resolvePostLoginPath({ role: "SUPPORT", is_temp_password: true })).toBe(
      "/change-password",
    );
  });

  it("redirects USER to profile", () => {
    expect(resolvePostLoginPath({ role: "USER", is_temp_password: false })).toBe("/profile");
  });

  it("redirects SUPERVISOR to admin settings parameters", () => {
    expect(resolvePostLoginPath({ role: "SUPERVISOR", is_temp_password: false })).toBe(
      "/admin/settings/parameters",
    );
  });

  it("redirects ADMIN to admin dashboard", () => {
    expect(resolvePostLoginPath({ role: "SUPPORT", is_temp_password: false })).toBe("/admin");
  });
});
