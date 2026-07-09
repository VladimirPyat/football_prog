import { describe, it, expect } from "vitest";
import {
  contestParametersSchema,
  createContestSchema,
  deriveRoundRobinStructure,
  matchResultSchema,
  roundBuilderSchema,
} from "@/lib/validation/admin";

describe("[UNIT-CREATE-SCHEMA] createContestSchema", () => {
  it("accepts name only", () => {
    expect(createContestSchema.safeParse({ name: "Test" }).success).toBe(true);
  });

  it("rejects empty name", () => {
    expect(createContestSchema.safeParse({ name: "", slug: "x" }).success).toBe(false);
  });

  it("strips unknown structural fields", () => {
    const result = createContestSchema.safeParse({ name: "X", total_teams: 8 });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data).toEqual({ name: "X" });
    }
  });
});

describe("[UNIT-PARAMS-SCHEMA] contestParametersSchema", () => {
  it("accepts valid round-robin values", () => {
    expect(
      contestParametersSchema.safeParse({
        total_teams: 8,
        matches_per_round: 4,
        total_rounds: 14,
        is_round_robin: true,
      }).success,
    ).toBe(true);
  });

  it("rejects round-robin with wrong matches_per_round", () => {
    const result = contestParametersSchema.safeParse({
      total_teams: 8,
      matches_per_round: 3,
      total_rounds: 14,
      is_round_robin: true,
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues.some((i) => i.message === "Должно быть = команды / 2")).toBe(true);
    }
  });

  it("accepts arbitrary mode with non-formula values", () => {
    expect(
      contestParametersSchema.safeParse({
        total_teams: 8,
        matches_per_round: 3,
        total_rounds: 5,
        is_round_robin: false,
      }).success,
    ).toBe(true);
  });
});

describe("[UNIT-ROUND-ROBIN-DERIVE] deriveRoundRobinStructure", () => {
  it("computes matches and rounds for 8 teams", () => {
    expect(deriveRoundRobinStructure(8)).toEqual({
      matches_per_round: 4,
      total_rounds: 14,
    });
  });

  it("recomputes when teams change 8→10", () => {
    expect(deriveRoundRobinStructure(10)).toEqual({
      matches_per_round: 5,
      total_rounds: 18,
    });
  });

  it("returns null for odd team count", () => {
    expect(deriveRoundRobinStructure(15)).toBeNull();
  });

  it("rejects round-robin with odd total_teams", () => {
    const result = contestParametersSchema.safeParse({
      total_teams: 15,
      matches_per_round: 7,
      total_rounds: 28,
      is_round_robin: true,
    });
    expect(result.success).toBe(false);
  });

  it("computes matches and rounds for 16 teams", () => {
    expect(deriveRoundRobinStructure(16)).toEqual({
      matches_per_round: 8,
      total_rounds: 30,
    });
  });
});

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
