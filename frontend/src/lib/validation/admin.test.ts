import { describe, it, expect } from "vitest";
import { matchResultSchema, roundBuilderSchema } from "@/lib/validation/admin";

describe("matchResultSchema", () => {
  const schema = matchResultSchema(20);

  it("rejects empty score fields (not coerced to 0)", () => {
    expect(schema.safeParse({ score1: "", score2: "" }).success).toBe(false);
    expect(schema.safeParse({ score1: 1, score2: "" }).success).toBe(false);
    expect(schema.safeParse({ score1: "", score2: 0 }).success).toBe(false);
  });

  it("accepts explicit 0:0", () => {
    const result = schema.safeParse({ score1: 0, score2: 0 });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data).toEqual({ score1: 0, score2: 0 });
    }
  });

  it("rejects out of range", () => {
    expect(schema.safeParse({ score1: 21, score2: 0 }).success).toBe(false);
  });
});

describe("roundBuilderSchema", () => {
  const schema = roundBuilderSchema(4, {});

  it("[T1] empty match date_time → human-readable error", () => {
    const result = schema.safeParse({
      number: 1,
      deadline: "2026-12-01T10:00:00.000Z",
      matches: [
        {
          team1_id: 1,
          team2_id: 2,
          date_time: "",
        },
        {
          team1_id: 3,
          team2_id: 4,
          date_time: "2026-11-01T15:00:00.000Z",
        },
      ],
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      const dateIssue = result.error.issues.find((i) => i.path.join(".") === "matches.0.date_time");
      expect(dateIssue?.message).toBe("Укажите дату и время для каждого матча");
    }
  });

  it("[T1] invalid date string → same human message", () => {
    const result = schema.safeParse({
      number: 1,
      deadline: "2026-12-01T10:00:00.000Z",
      matches: [
        { team1_id: 1, team2_id: 2, date_time: "invalid" },
        { team1_id: 3, team2_id: 4, date_time: "2026-11-01T15:00:00.000Z" },
      ],
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      const hasDateError = result.error.issues.some(
        (i) => i.message === "Укажите дату и время для каждого матча",
      );
      expect(hasDateError).toBe(true);
    }
  });
});
