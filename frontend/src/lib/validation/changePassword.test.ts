import { describe, it, expect } from "vitest";
import { changePasswordSchema } from "@/lib/validation/changePassword";

describe("changePasswordSchema", () => {
  it("rejects password mismatch on confirm", () => {
    const result = changePasswordSchema.safeParse({
      old_password: "oldpass",
      new_password: "newpassword",
      confirm: "different",
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      const confirmIssue = result.error.issues.find((i) => i.path[0] === "confirm");
      expect(confirmIssue?.message).toBe("Пароли не совпадают");
    }
  });

  it("rejects new password shorter than 8 characters", () => {
    const result = changePasswordSchema.safeParse({
      old_password: "oldpass",
      new_password: "short",
      confirm: "short",
    });
    expect(result.success).toBe(false);
  });

  it("accepts valid change password payload", () => {
    const result = changePasswordSchema.safeParse({
      old_password: "temppass",
      new_password: "newpassword1",
      confirm: "newpassword1",
    });
    expect(result.success).toBe(true);
  });
});
