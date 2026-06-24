import { describe, it, expect } from "vitest";
import {
  deadlineErrorMessage,
  getDeadlineRuleHours,
  isDeadlineValid,
} from "@/lib/admin/deadlineRule";

describe("deadlineRule", () => {
  const matchTime = "2026-07-01T18:00:00.000Z";

  it("reads deadline_rule_hours from rules_json", () => {
    expect(getDeadlineRuleHours({ contest_structure: { deadline_rule_hours: 48 } })).toBe(48);
    expect(getDeadlineRuleHours({})).toBe(24);
  });

  it("passes when deadline is exactly rule hours before first match", () => {
    const deadline = "2026-07-01T06:00:00.000Z"; // 12h before 18:00 with 12h rule
    expect(isDeadlineValid(deadline, matchTime, 12)).toBe(true);
  });

  it("fails when deadline is after cutoff", () => {
    const deadline = "2026-07-01T12:00:00.000Z"; // only 6h before with 12h rule
    expect(isDeadlineValid(deadline, matchTime, 12)).toBe(false);
  });

  it("passes at 24h boundary with default rule", () => {
    const deadline = "2026-06-30T18:00:00.000Z";
    expect(isDeadlineValid(deadline, matchTime, 24)).toBe(true);
  });

  it("fails one millisecond past boundary", () => {
    const matchMs = Date.parse(matchTime);
    const deadline = new Date(matchMs - 24 * 3_600_000 + 1).toISOString();
    expect(isDeadlineValid(deadline, matchTime, 24)).toBe(false);
  });

  it("formats Russian error message with hours", () => {
    expect(deadlineErrorMessage(48)).toContain("48");
  });
});
