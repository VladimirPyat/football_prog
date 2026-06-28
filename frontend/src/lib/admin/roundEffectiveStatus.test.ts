import { describe, expect, it } from "vitest";
import {
  effectiveRoundStatus,
  isDeadlinePassedNow,
  isPhaseRoundStatus,
} from "@/lib/admin/roundEffectiveStatus";

const activeRound = {
  status: "ACTIVE" as const,
  deadline: "2026-06-28T17:00:00.000Z",
};

describe("isDeadlinePassedNow", () => {
  it("true when now >= deadline", () => {
    const now = new Date("2026-06-28T18:00:00.000Z");
    expect(isDeadlinePassedNow("2026-06-28T17:00:00.000Z", now)).toBe(true);
  });

  it("false when now < deadline", () => {
    const now = new Date("2026-06-28T16:00:00.000Z");
    expect(isDeadlinePassedNow("2026-06-28T17:00:00.000Z", now)).toBe(false);
  });

  it("naive API ISO is UTC (matches backend)", () => {
    const now = new Date("2026-06-28T16:00:00.000Z");
    expect(isDeadlinePassedNow("2026-06-28T17:00:00", now)).toBe(false);
    const after = new Date("2026-06-28T17:00:00.000Z");
    expect(isDeadlinePassedNow("2026-06-28T17:00:00", after)).toBe(true);
  });
});

describe("effectiveRoundStatus", () => {
  it("ACTIVE + deadlinePassed → CLOSED", () => {
    expect(effectiveRoundStatus(activeRound, true)).toBe("CLOSED");
  });

  it("ACTIVE + explicit false → ACTIVE", () => {
    expect(effectiveRoundStatus(activeRound, false)).toBe("ACTIVE");
  });

  it("ACTIVE infers passed from deadline timestamp", () => {
    const now = new Date("2026-06-28T18:00:00.000Z");
    expect(isDeadlinePassedNow(activeRound.deadline, now)).toBe(true);
    expect(effectiveRoundStatus(activeRound, isDeadlinePassedNow(activeRound.deadline, now))).toBe(
      "CLOSED",
    );
  });

  it("CLOSED unchanged", () => {
    expect(effectiveRoundStatus({ status: "CLOSED", deadline: activeRound.deadline }, true)).toBe(
      "CLOSED",
    );
  });
});

describe("isPhaseRoundStatus", () => {
  it("returns true for CLOSED, CALCULATED, PUBLISHED", () => {
    expect(isPhaseRoundStatus("CLOSED")).toBe(true);
    expect(isPhaseRoundStatus("CALCULATED")).toBe(true);
    expect(isPhaseRoundStatus("PUBLISHED")).toBe(true);
  });

  it("returns false for DRAFT and ACTIVE", () => {
    expect(isPhaseRoundStatus("DRAFT")).toBe(false);
    expect(isPhaseRoundStatus("ACTIVE")).toBe(false);
  });
});
