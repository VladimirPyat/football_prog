import { describe, it, expect } from "vitest";
import { canEnterMatchResult, roundHasStartedMatches } from "@/lib/admin/matchResultsGating";

const pastKickoff = new Date("2020-01-01T12:00:00Z");
const futureKickoff = new Date("2099-06-01T12:00:00Z");

describe("canEnterMatchResult", () => {
  it("[UNIT-MATCH-KICKOFF-GATE] CLOSED + before kickoff → false", () => {
    expect(
      canEnterMatchResult(
        { status: "SCHEDULED", date_time: futureKickoff.toISOString() },
        { status: "CLOSED" },
        new Date(),
      ),
    ).toBe(false);
  });

  it("[UNIT-MATCH-KICKOFF-GATE] CLOSED + after kickoff → true", () => {
    expect(
      canEnterMatchResult(
        { status: "SCHEDULED", date_time: pastKickoff.toISOString() },
        { status: "CLOSED" },
        new Date(),
      ),
    ).toBe(true);
  });

  it("[UI-RESULTS-REEDIT-CLOSED] CLOSED + FINISHED + kickoff passed → true (re-edit)", () => {
    expect(
      canEnterMatchResult(
        { status: "FINISHED", date_time: pastKickoff.toISOString() },
        { status: "CLOSED" },
        new Date(),
      ),
    ).toBe(true);
  });

  it("[UNIT-MATCH-KICKOFF-GATE] CLOSED + VOID → false", () => {
    expect(
      canEnterMatchResult(
        { status: "VOID", date_time: pastKickoff.toISOString() },
        { status: "CLOSED" },
        new Date(),
      ),
    ).toBe(false);
  });

  it("[UNIT-MATCH-KICKOFF-GATE] CLOSED + CANCELED → false", () => {
    expect(
      canEnterMatchResult(
        { status: "CANCELED", date_time: pastKickoff.toISOString() },
        { status: "CLOSED" },
        new Date(),
      ),
    ).toBe(false);
  });

  it("[API-RESULT-CALCULATED] CALCULATED + FINISHED → true", () => {
    expect(
      canEnterMatchResult(
        { status: "FINISHED", date_time: pastKickoff.toISOString() },
        { status: "CALCULATED" },
      ),
    ).toBe(true);
  });

  it("CALCULATED + SCHEDULED → false", () => {
    expect(
      canEnterMatchResult(
        { status: "SCHEDULED", date_time: pastKickoff.toISOString() },
        { status: "CALCULATED" },
      ),
    ).toBe(false);
  });

  it("PUBLISHED → false", () => {
    expect(
      canEnterMatchResult(
        { status: "FINISHED", date_time: pastKickoff.toISOString() },
        { status: "PUBLISHED" },
      ),
    ).toBe(false);
  });

  it("[UNIT-MATCH-KICKOFF-GATE] ACTIVE → false", () => {
    expect(
      canEnterMatchResult(
        { status: "SCHEDULED", date_time: pastKickoff.toISOString() },
        { status: "ACTIVE" },
      ),
    ).toBe(false);
  });

  it("[UNIT-MATCH-KICKOFF-GATE] DRAFT → false", () => {
    expect(
      canEnterMatchResult(
        { status: "SCHEDULED", date_time: pastKickoff.toISOString() },
        { status: "DRAFT" },
      ),
    ).toBe(false);
  });
});

describe("roundHasStartedMatches", () => {
  it("[UNIT-MATCH-KICKOFF-GATE] one past kickoff → true", () => {
    expect(
      roundHasStartedMatches([
        { date_time: futureKickoff.toISOString() },
        { date_time: pastKickoff.toISOString() },
      ]),
    ).toBe(true);
  });

  it("[UNIT-MATCH-KICKOFF-GATE] all future kickoffs → false", () => {
    expect(roundHasStartedMatches([{ date_time: futureKickoff.toISOString() }], new Date())).toBe(
      false,
    );
  });
});
