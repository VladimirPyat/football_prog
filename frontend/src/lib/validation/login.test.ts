import { describe, it, expect } from "vitest";
import { loginSchema } from "@/lib/validation/login";

describe("loginSchema", () => {
  it("rejects empty login", () => {
    const result = loginSchema.safeParse({ login: "", password: "secret" });
    expect(result.success).toBe(false);
  });

  it("rejects empty password", () => {
    const result = loginSchema.safeParse({ login: "user", password: "" });
    expect(result.success).toBe(false);
  });

  it("accepts valid credentials", () => {
    const result = loginSchema.safeParse({ login: "user", password: "pass" });
    expect(result.success).toBe(true);
  });
});
