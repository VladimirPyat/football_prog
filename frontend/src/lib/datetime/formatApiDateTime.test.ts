import { describe, expect, it, vi, afterEach } from "vitest";
import { fromDatetimeLocal, toDatetimeLocal } from "@/lib/datetime/formatApiDateTime";

describe("formatApiDateTime with Europe/Moscow", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("displays and round-trips 17:00 Moscow as 14:00Z", () => {
    vi.stubEnv("NEXT_PUBLIC_DISPLAY_TIMEZONE", "Europe/Moscow");
    vi.stubEnv("NEXT_PUBLIC_API_TIMESTAMP_TIMEZONE", "UTC");

    const apiIso = "2026-06-28T14:00:00.000Z";
    expect(toDatetimeLocal(apiIso)).toBe("2026-06-28T17:00");
    expect(fromDatetimeLocal("2026-06-28T17:00")).toBe("2026-06-28T14:00:00.000Z");
  });
});
