import { describe, it, expect } from "vitest";
import {
  canChangeDeadline,
  deadlineChangeClosedMessage,
  deadlineErrorMessage,
  getDeadlineRuleHours,
  isDeadlineValid,
  isDeadlinePlacementValid,
} from "@/lib/admin/deadlineRule";

describe("deadlineRule", () => {
  const matchTime = "2026-07-01T18:00:00.000Z";

  it("reads deadline_rule_hours from rules_json", () => {
    expect(getDeadlineRuleHours({ contest_structure: { deadline_rule_hours: 48 } })).toBe(48);
    expect(getDeadlineRuleHours({})).toBe(24);
  });

  // ── Placement rule: deadline must be strictly before first match ──────────

  it("[UNIT-DEADLINE-PLACEMENT] passes when deadline is 1h before first match", () => {
    const deadline = "2026-07-01T17:00:00.000Z"; // 1h before 18:00
    expect(isDeadlineValid(deadline, matchTime)).toBe(true);
  });

  it("[UNIT-DEADLINE-PLACEMENT] passes when deadline is 23h before first match (no 24h gap)", () => {
    const deadline = "2026-06-30T19:00:00.000Z"; // 23h before 18:00
    expect(isDeadlineValid(deadline, matchTime)).toBe(true);
  });

  it("[UNIT-DEADLINE-PLACEMENT] passes at 24h before first match", () => {
    const deadline = "2026-06-30T18:00:00.000Z"; // exactly 24h before
    expect(isDeadlineValid(deadline, matchTime)).toBe(true);
  });

  it("[UNIT-DEADLINE-PLACEMENT] passes even 25h before first match", () => {
    const deadline = "2026-06-30T17:00:00.000Z"; // 25h before
    expect(isDeadlineValid(deadline, matchTime)).toBe(true);
  });

  it("[UNIT-DEADLINE-PLACEMENT] fails when deadline equals first match time", () => {
    expect(isDeadlineValid(matchTime, matchTime)).toBe(false);
  });

  it("[UNIT-DEADLINE-PLACEMENT] min gap from rules_json (default 0)", () => {
    const deadline = "2026-07-01T17:59:00.000Z";
    const match = "2026-07-01T18:00:00.000Z";
    expect(isDeadlinePlacementValid(deadline, match, {})).toBe(true);
    expect(
      isDeadlinePlacementValid(deadline, match, {
        contest_structure: { deadline_min_before_match_minutes: 2 },
      }),
    ).toBe(false);
  });

  it("[UNIT-DEADLINE-PLACEMENT] fails when deadline is after first match", () => {
    const deadline = "2026-07-01T19:00:00.000Z"; // 1h after
    expect(isDeadlineValid(deadline, matchTime)).toBe(false);
  });

  it("formats Russian error message (placement)", () => {
    const msg = deadlineErrorMessage();
    expect(msg).toContain("раньше");
    expect(msg).toContain("матча");
  });

  // ── Lockout rule: now <= currentDeadline - ruleHours ─────────────────────

  it("[UNIT-DEADLINE-LOCKOUT] change allowed when well inside window (48h to current deadline)", () => {
    const now = new Date("2026-06-29T12:00:00.000Z");
    const currentDeadline = "2026-07-01T12:00:00.000Z"; // 48h away
    expect(canChangeDeadline(now, currentDeadline, 24)).toBe(true);
  });

  it("[UNIT-DEADLINE-LOCKOUT] change allowed at exactly the cutoff boundary", () => {
    const now = new Date("2026-06-30T12:00:00.000Z");
    const currentDeadline = "2026-07-01T12:00:00.000Z"; // exactly 24h away → now == cutoff
    expect(canChangeDeadline(now, currentDeadline, 24)).toBe(true);
  });

  it("[UNIT-DEADLINE-LOCKOUT] change blocked 1ms past boundary", () => {
    const cutoffMs = Date.parse("2026-06-30T12:00:00.000Z");
    const now = new Date(cutoffMs + 1);
    const currentDeadline = "2026-07-01T12:00:00.000Z";
    expect(canChangeDeadline(now, currentDeadline, 24)).toBe(false);
  });

  it("[UNIT-DEADLINE-LOCKOUT] change blocked when current deadline is 10h away (within 24h)", () => {
    const now = new Date("2026-06-30T12:00:00.000Z");
    const currentDeadline = "2026-06-30T22:00:00.000Z"; // 10h from now
    expect(canChangeDeadline(now, currentDeadline, 24)).toBe(false);
  });

  it("formats lockout message with ruleHours", () => {
    const msg = deadlineChangeClosedMessage(48);
    expect(msg).toContain("48");
    expect(msg).toContain("дедлайна");
  });
});
