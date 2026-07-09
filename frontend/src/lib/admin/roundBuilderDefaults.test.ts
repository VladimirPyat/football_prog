import { describe, expect, it } from "vitest";
import { nextMatchDateTime } from "./roundBuilderDefaults";

describe("nextMatchDateTime", () => {
  it("copies last match datetime when present", () => {
    const result = nextMatchDateTime(
      [{ date_time: "" }, { date_time: "2026-07-10T12:00:00.000Z" }],
      "",
    );
    expect(result).toBe("2026-07-10T12:00:00.000Z");
  });

  it("falls back to deadline when no match times", () => {
    const result = nextMatchDateTime([{ date_time: "" }], "2026-07-10T15:30");
    expect(result).toContain("2026-07-10");
  });

  it("returns empty when nothing to copy", () => {
    expect(nextMatchDateTime([], "")).toBe("");
  });
});
