import { describe, expect, it } from "vitest";
import { roundHasVisiblePostponements } from "@/lib/admin/roundScoringPending";
import type { MatchOut } from "@/types/api";

const match = (status: MatchOut["status"]): MatchOut => ({
  id: 1,
  team1: "A",
  team2: "B",
  date_time: "2026-01-01T12:00:00Z",
  score1: null,
  score2: null,
  status,
});

describe("roundHasVisiblePostponements", () => {
  it("true when POSTPONED present", () => {
    expect(roundHasVisiblePostponements([match("FINISHED"), match("POSTPONED")])).toBe(true);
  });

  it("false when only finished and canceled", () => {
    expect(roundHasVisiblePostponements([match("FINISHED"), match("CANCELED")])).toBe(false);
  });
});
