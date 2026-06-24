import { describe, it, expect, vi, beforeEach } from "vitest";
import { collectPostponedMatches } from "@/lib/admin/collectPostponedMatches";
import { apiGet } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  apiGet: vi.fn(),
}));

const mockedApiGet = vi.mocked(apiGet);

describe("collectPostponedMatches", () => {
  beforeEach(() => {
    mockedApiGet.mockReset();
  });

  it("returns only POSTPONED matches across rounds", async () => {
    mockedApiGet
      .mockResolvedValueOnce([
        { id: 1, number: 1, contest_id: 1, deadline: "", status: "ACTIVE", matches_count: 2 },
        { id: 2, number: 2, contest_id: 1, deadline: "", status: "CLOSED", matches_count: 1 },
      ])
      .mockResolvedValueOnce({
        matches: [
          {
            id: 10,
            team1: "A",
            team2: "B",
            date_time: "2026-01-01T12:00:00Z",
            score1: null,
            score2: null,
            status: "POSTPONED",
          },
          {
            id: 11,
            team1: "C",
            team2: "D",
            date_time: "2026-01-02T12:00:00Z",
            score1: null,
            score2: null,
            status: "SCHEDULED",
          },
        ],
      })
      .mockResolvedValueOnce({
        matches: [
          {
            id: 20,
            team1: "E",
            team2: "F",
            date_time: "2026-01-03T12:00:00Z",
            score1: null,
            score2: null,
            status: "POSTPONED",
          },
        ],
      });

    const result = await collectPostponedMatches(1);

    expect(result).toHaveLength(2);
    expect(result.every((m) => m.status === "POSTPONED")).toBe(true);
    expect(result[0].roundNumber).toBe(1);
    expect(result[1].roundNumber).toBe(2);
  });

  it("returns empty when no postponed matches", async () => {
    mockedApiGet
      .mockResolvedValueOnce([
        { id: 1, number: 1, contest_id: 1, deadline: "", status: "ACTIVE", matches_count: 1 },
      ])
      .mockResolvedValueOnce({
        matches: [
          {
            id: 10,
            team1: "A",
            team2: "B",
            date_time: "2026-01-01T12:00:00Z",
            score1: null,
            score2: null,
            status: "FINISHED",
          },
        ],
      });

    const result = await collectPostponedMatches(1);
    expect(result).toEqual([]);
  });
});
