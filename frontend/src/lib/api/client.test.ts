import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { AppError, apiFetch } from "@/lib/api/client";
import { parseErrorDetail } from "@/lib/api/errors";
import { UNAUTHORIZED_EVENT } from "@/lib/auth/token";

describe("parseErrorDetail", () => {
  it("parses string detail with code", () => {
    const result = parseErrorDetail({ detail: "Ошибка", code: "NOT_FOUND" });
    expect(result).toEqual({ detail: "Ошибка", code: "NOT_FOUND" });
  });

  it("parses Pydantic 422 array detail", () => {
    const result = parseErrorDetail({
      detail: [{ loc: ["body", "email"], msg: "Invalid email", type: "value_error" }],
    });
    expect(result.detail).toContain("Invalid email");
  });

  it("returns unknown for empty body", () => {
    expect(parseErrorDetail(null).detail).toBe("Unknown error");
  });
});

describe("AppError", () => {
  it("stores status, detail, and code", () => {
    const err = new AppError(400, "Bad request", "VALIDATION_ERROR");
    expect(err.status).toBe(400);
    expect(err.detail).toBe("Bad request");
    expect(err.code).toBe("VALIDATION_ERROR");
    expect(err.message).toBe("Bad request");
  });
});

describe("apiFetch 401", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.stubGlobal("localStorage", {
      getItem: vi.fn(() => "token"),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    });
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.unstubAllGlobals();
  });

  it("dispatches fp:unauthorized on 401", async () => {
    const handler = vi.fn();
    window.addEventListener(UNAUTHORIZED_EVENT, handler);

    global.fetch = vi.fn().mockResolvedValue({
      status: 401,
      ok: false,
      json: async () => ({}),
    });

    await expect(apiFetch("/api/v1/auth/me")).rejects.toThrow(AppError);
    expect(handler).toHaveBeenCalled();

    window.removeEventListener(UNAUTHORIZED_EVENT, handler);
  });
});
