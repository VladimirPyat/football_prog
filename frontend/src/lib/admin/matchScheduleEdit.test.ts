import { describe, it, expect } from "vitest";
import {
  canCancelMatch,
  canMarkPostponed,
  canRescheduleMatch,
  canRestoreMatchStatus,
  isLongPostponement,
} from "@/lib/admin/matchScheduleEdit";

const now = new Date("2026-06-27T12:00:00.000Z");
const futureKickoff = "2026-06-27T18:00:00.000Z";
const pastKickoff = "2026-06-27T10:00:00.000Z";

describe("matchScheduleEdit", () => {
  it("allows reschedule before kickoff regardless of round deadline", () => {
    expect(canRescheduleMatch({ date_time: futureKickoff, status: "SCHEDULED" }, now)).toBe(true);
  });

  it("blocks reschedule after kickoff", () => {
    expect(canRescheduleMatch({ date_time: pastKickoff, status: "SCHEDULED" }, now)).toBe(false);
  });

  it("allows cancel for scheduled match even after kickoff", () => {
    expect(canCancelMatch({ status: "SCHEDULED" })).toBe(true);
    expect(canCancelMatch({ status: "POSTPONED" })).toBe(true);
  });

  it("blocks cancel for terminal statuses", () => {
    expect(canCancelMatch({ status: "CANCELED" })).toBe(false);
    expect(canCancelMatch({ status: "FINISHED" })).toBe(false);
  });

  it("restore only for admin on canceled/postponed", () => {
    expect(canRestoreMatchStatus({ status: "CANCELED" }, false)).toBe(false);
    expect(canRestoreMatchStatus({ status: "CANCELED" }, true)).toBe(true);
    expect(canRestoreMatchStatus({ status: "SCHEDULED" }, true)).toBe(false);
  });

  it("mark postponed only from scheduled", () => {
    expect(canMarkPostponed({ status: "SCHEDULED" })).toBe(true);
    expect(canMarkPostponed({ status: "POSTPONED" })).toBe(false);
  });

  it("detects long postponement (>= 7 days)", () => {
    expect(
      isLongPostponement("2026-06-27T18:00:00.000Z", "2026-07-05T18:00:00.000Z"),
    ).toBe(true);
    expect(
      isLongPostponement("2026-06-27T18:00:00.000Z", "2026-06-27T21:00:00.000Z"),
    ).toBe(false);
  });
});
