import { describe, it, expect } from "vitest";
import { contactsSchema } from "@/lib/validation/contacts";

describe("contactsSchema", () => {
  it("rejects invalid email", () => {
    const result = contactsSchema.safeParse({
      email: "not-an-email",
      notify_enabled: false,
    });
    expect(result.success).toBe(false);
  });

  it("accepts empty email", () => {
    const result = contactsSchema.safeParse({
      email: "",
      notify_enabled: true,
    });
    expect(result.success).toBe(true);
  });

  it("accepts valid email", () => {
    const result = contactsSchema.safeParse({
      email: "user@example.com",
      vk_id: "123",
      tg_id: "@user",
      notify_enabled: false,
    });
    expect(result.success).toBe(true);
  });
});
