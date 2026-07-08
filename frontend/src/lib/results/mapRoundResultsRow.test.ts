import { describe, expect, it } from "vitest";
import {
  mapRoundResultsRow,
  mapRoundResultsRows,
  roundResultsPointsMissing,
} from "@/lib/results/mapRoundResultsRow";
import type { MatchOut, RoundResultRowOut } from "@/types/api";

const matches: MatchOut[] = [
  {
    id: 10,
    team1: "A",
    team2: "B",
    date_time: "2026-01-01T12:00:00Z",
    score1: 1,
    score2: 0,
    status: "FINISHED",
  },
  {
    id: 20,
    team1: "C",
    team2: "D",
    date_time: "2026-01-01T15:00:00Z",
    score1: 2,
    score2: 2,
    status: "FINISHED",
  },
];

const baseRow: RoundResultRowOut = {
  user_id: 1,
  user_name: "Иванов",
  points: [
    { match_id: 10, base_points: 4 },
    { match_id: 20, base_points: 8 },
  ],
  bonus1: 1,
  bonus2: 2,
  bonus3: null,
  total_without_bonus3: 12,
  total: 15,
  correct_outcomes: 2,
};

describe("mapRoundResultsRow", () => {
  it("aligns points[] to match order as match_points[]", () => {
    const row = mapRoundResultsRow(baseRow, [10, 20]);
    expect(row.match_points).toEqual([4, 8]);
    expect(row.total_without_bonus).toBe(12);
    expect(row.total).toBe(15);
  });

  it("preserves null base_points and bonus3", () => {
    const row = mapRoundResultsRow(
      {
        ...baseRow,
        points: [
          { match_id: 10, base_points: null },
          { match_id: 20, base_points: 0 },
        ],
        bonus3: null,
      },
      [10, 20],
    );
    expect(row.match_points).toEqual([null, 0]);
    expect(row.bonus3).toBeNull();
  });

  it("fills missing match ids with null", () => {
    const row = mapRoundResultsRow(
      { ...baseRow, points: [{ match_id: 10, base_points: 4 }] },
      [10, 20],
    );
    expect(row.match_points).toEqual([4, null]);
  });

  it("mapRoundResultsRows maps all rows", () => {
    const rows = mapRoundResultsRows([baseRow, { ...baseRow, user_name: "Петров" }], [10, 20]);
    expect(rows).toHaveLength(2);
    expect(rows[0].user_name).toBe("Иванов");
  });

  it("roundResultsPointsMissing detects empty points arrays", () => {
    expect(roundResultsPointsMissing(matches, [{ ...baseRow, points: [] }])).toBe(true);
    expect(roundResultsPointsMissing(matches, [baseRow])).toBe(false);
    expect(roundResultsPointsMissing([], [baseRow])).toBe(false);
  });
});
