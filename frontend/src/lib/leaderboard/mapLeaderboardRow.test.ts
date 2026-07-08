import { describe, expect, it } from "vitest";
import {
  hasLeaderboardCountColumns,
  mapLeaderboardRow,
  mapLeaderboardRows,
} from "@/lib/leaderboard/mapLeaderboardRow";
import type { LeaderboardEntryOut } from "@/types/api";

const baseEntry: LeaderboardEntryOut = {
  user_id: 1,
  user_name: "Иванов И.И.",
  points_base: 40,
  bonus1: 2,
  bonus2: 3,
  bonus3: 5,
  total_without_bonus3: 45,
  total_bonus_points: 10,
  total_with_bonus3: 50,
  correct_outcomes: 6,
  count_exact_high: 1,
  count_exact: 2,
  count_diff: 3,
  count_outcome: 4,
  rank: 1,
  predictions_count: 8,
  exceptional_tiebreak_points: 0,
  tiebreaker_status: null,
};

describe("mapLeaderboardRow", () => {
  it("maps API row to table row with B4 count fields preserved", () => {
    const row = mapLeaderboardRow(baseEntry);
    expect(row).toEqual({
      rank: 1,
      user_name: "Иванов И.И.",
      predictions_count: 8,
      count_exact_high: 1,
      count_exact: 2,
      count_diff: 3,
      count_outcome: 4,
      bonus1: 2,
      bonus2: 3,
      bonus3: 5,
      points_base: 40,
      total_bonus_points: 10,
      total_with_bonus3: 50,
    });
  });

  it("derives total_bonus_points when API field is missing", () => {
    const legacy: LeaderboardEntryOut = {
      ...baseEntry,
      total_bonus_points: undefined,
    };
    expect(mapLeaderboardRow(legacy).total_bonus_points).toBe(10);
  });

  it("defaults missing count_* fields to zero", () => {
    const legacy: LeaderboardEntryOut = {
      ...baseEntry,
      count_exact_high: undefined,
      count_exact: undefined,
      count_diff: undefined,
      count_outcome: undefined,
    };
    const row = mapLeaderboardRow(legacy);
    expect(row.count_exact_high).toBe(0);
    expect(row.count_exact).toBe(0);
    expect(row.count_diff).toBe(0);
    expect(row.count_outcome).toBe(0);
  });

  it("mapLeaderboardRows maps all entries", () => {
    const rows = mapLeaderboardRows([baseEntry, { ...baseEntry, rank: 2, user_name: "Петров" }]);
    expect(rows).toHaveLength(2);
    expect(rows[1].rank).toBe(2);
  });

  it("hasLeaderboardCountColumns is false when count_* absent", () => {
    const legacy: LeaderboardEntryOut = {
      ...baseEntry,
      count_exact_high: undefined,
      count_exact: undefined,
      count_diff: undefined,
      count_outcome: undefined,
    };
    expect(hasLeaderboardCountColumns([legacy])).toBe(false);
    expect(hasLeaderboardCountColumns([baseEntry])).toBe(true);
  });
});
