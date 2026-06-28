import { describe, expect, it } from "vitest";
import { parseApiUtc } from "@/lib/datetime/parseApiUtc";

describe("parseApiUtc", () => {
  it("parses explicit Z as UTC", () => {
    expect(parseApiUtc("2026-06-28T17:00:00.000Z")).toBe(Date.UTC(2026, 5, 28, 17, 0, 0, 0));
  });

  it("treats naive ISO as UTC (matches backend _ensure_utc)", () => {
    expect(parseApiUtc("2026-06-28T17:00:00")).toBe(Date.UTC(2026, 5, 28, 17, 0, 0, 0));
  });

  it("returns NaN for empty input", () => {
    expect(Number.isNaN(parseApiUtc(""))).toBe(true);
  });
});
