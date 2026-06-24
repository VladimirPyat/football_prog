import { describe, it, expect } from "vitest";
import { deriveAdminUiMode } from "@/lib/admin/deriveAdminUiMode";
import type { ContestOut, RoundOut } from "@/types/api";

const baseContest: ContestOut = {
  id: 1,
  name: "Test",
  slug: null,
  is_locked: false,
  status: "RUNNING",
  paused_at: null,
  finished_at: null,
  total_teams: 8,
  matches_per_round: 4,
  total_rounds: 14,
  is_round_robin: true,
  rules_json: { contest_structure: { deadline_rule_hours: 24 } },
};

const draftRound: RoundOut = {
  id: 1,
  contest_id: 1,
  number: 1,
  deadline: "2026-06-01T12:00:00.000Z",
  status: "DRAFT",
  matches_count: 4,
};

const activeRound: RoundOut = { ...draftRound, status: "ACTIVE" };
const publishedRound: RoundOut = { ...draftRound, status: "PUBLISHED" };

describe("deriveAdminUiMode", () => {
  it("allows setup when contest is unlocked", () => {
    const mode = deriveAdminUiMode({ contest: baseContest, round: null });
    expect(mode.setupReadonly).toBe(false);
    expect(mode.showLockBanner).toBe(false);
  });

  it("locks setup when is_locked", () => {
    const mode = deriveAdminUiMode({
      contest: { ...baseContest, is_locked: true },
      round: null,
    });
    expect(mode.setupReadonly).toBe(true);
    expect(mode.showLockBanner).toBe(true);
  });

  it("disables mutations when paused", () => {
    const mode = deriveAdminUiMode({
      contest: { ...baseContest, status: "PAUSED" },
      round: activeRound,
    });
    expect(mode.disableAllMutations).toBe(true);
    expect(mode.showPausedBanner).toBe(true);
    expect(mode.canEditMatchStatusAndDate).toBe(false);
  });

  it("allows structure edit only in DRAFT", () => {
    const draft = deriveAdminUiMode({ contest: baseContest, round: draftRound });
    expect(draft.canEditRoundStructure).toBe(true);
    expect(draft.canEditMatchStatusAndDate).toBe(false);

    const active = deriveAdminUiMode({ contest: baseContest, round: activeRound });
    expect(active.canEditRoundStructure).toBe(false);
    expect(active.canEditMatchStatusAndDate).toBe(true);
    expect(active.showActiveRoundHint).toBe(true);
  });

  it("enables results workflow for CLOSED round", () => {
    const closed: RoundOut = { ...draftRound, status: "CLOSED" };
    const mode = deriveAdminUiMode({ contest: baseContest, round: closed });
    expect(mode.canEnterResults).toBe(true);
    expect(mode.canCalculate).toBe(true);
    expect(mode.canPublish).toBe(false);
  });

  it("shows applied badge for PUBLISHED", () => {
    const mode = deriveAdminUiMode({ contest: baseContest, round: publishedRound });
    expect(mode.showAppliedBadge).toBe(true);
    expect(mode.resultsReadonly).toBe(true);
    expect(mode.canVoidMatch).toBe(true);
  });

  it("allows void on PUBLISHED but not when paused", () => {
    const published = deriveAdminUiMode({ contest: baseContest, round: publishedRound });
    expect(published.canVoidMatch).toBe(true);
    expect(published.resultsReadonly).toBe(true);

    const paused = deriveAdminUiMode({
      contest: { ...baseContest, status: "PAUSED" },
      round: publishedRound,
    });
    expect(paused.canVoidMatch).toBe(false);
  });
});
