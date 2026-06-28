import { describe, expect, it } from "vitest";
import { utcToWallDateTimeLocal, wallDateTimeLocalToUtc } from "@/lib/datetime/zonedWallTime";

describe("zonedWallTime Europe/Moscow", () => {
  it("converts wall 17:00 to 14:00Z in summer", () => {
    const utc = wallDateTimeLocalToUtc("2026-06-28T17:00", "Europe/Moscow");
    expect(utc.toISOString()).toBe("2026-06-28T14:00:00.000Z");
  });

  it("converts 14:00Z to wall 17:00", () => {
    expect(utcToWallDateTimeLocal(new Date("2026-06-28T14:00:00.000Z"), "Europe/Moscow")).toBe(
      "2026-06-28T17:00",
    );
  });
});
