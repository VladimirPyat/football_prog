import { describe, expect, it } from "vitest";
import { scoreInputSchema } from "./score";

describe("scoreInputSchema", () => {
  const max = 15;

  it("[UNIT-SCORE-RANGE] accepts 0", () => {
    const r = scoreInputSchema(max).safeParse(0);
    expect(r.success).toBe(true);
  });

  it("[UNIT-SCORE-RANGE] accepts max", () => {
    const r = scoreInputSchema(max).safeParse(max);
    expect(r.success).toBe(true);
  });

  it("[UNIT-SCORE-RANGE] rejects empty (not coerced to 0)", () => {
    const r = scoreInputSchema(max).safeParse("");
    expect(r.success).toBe(false);
  });

  it("[UNIT-SCORE-RANGE] rejects max+1", () => {
    const r = scoreInputSchema(max).safeParse(max + 1);
    expect(r.success).toBe(false);
  });

  it("[UNIT-SCORE-RANGE] rejects non-integer", () => {
    const r = scoreInputSchema(max).safeParse(1.5);
    expect(r.success).toBe(false);
  });
});
