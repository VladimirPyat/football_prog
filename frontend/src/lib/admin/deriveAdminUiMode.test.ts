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

/** Deadline is 48h from now — change window open. */
const farDeadline = new Date(Date.now() + 48 * 3_600_000).toISOString();
/** Deadline is 10h from now — change window CLOSED (within 24h). */
const nearDeadline = new Date(Date.now() + 10 * 3_600_000).toISOString();

const roundDefaults = {
  kind: "REGULAR" as const,
  supplementary_index: null,
  source_round_numbers: [] as number[],
};

const draftRound: RoundOut = {
  id: 1,
  contest_id: 1,
  number: 1,
  deadline: farDeadline,
  status: "DRAFT",
  matches_count: 4,
  ...roundDefaults,
};

const activeRoundFarDeadline: RoundOut = { ...draftRound, status: "ACTIVE", deadline: farDeadline };
const activeRoundNearDeadline: RoundOut = {
  ...draftRound,
  status: "ACTIVE",
  deadline: nearDeadline,
};
const publishedRound: RoundOut = { ...draftRound, status: "PUBLISHED" };

describe("deriveAdminUiMode", () => {
  it("locks setup when RUNNING even if unlocked", () => {
    const mode = deriveAdminUiMode({ contest: baseContest, round: null });
    expect(mode.setupReadonly).toBe(true);
    expect(mode.showSetupLockBanner).toBe(false);
  });

  it("allows setup when contest is DRAFT and unlocked", () => {
    const mode = deriveAdminUiMode({
      contest: { ...baseContest, status: "DRAFT", is_locked: false },
      round: null,
    });
    expect(mode.setupReadonly).toBe(false);
  });

  it("locks setup when is_locked", () => {
    const mode = deriveAdminUiMode({
      contest: { ...baseContest, is_locked: true },
      round: null,
    });
    expect(mode.setupReadonly).toBe(true);
    expect(mode.showSetupLockBanner).toBe(true);
  });

  it("disables mutations when paused", () => {
    const mode = deriveAdminUiMode({
      contest: { ...baseContest, status: "PAUSED" },
      round: activeRoundFarDeadline,
    });
    expect(mode.disableAllMutations).toBe(true);
    expect(mode.showPausedBanner).toBe(true);
    expect(mode.canEditMatchStatusAndDate).toBe(false);
  });

  it("[UNIT-UI-MODE-ACTIVE] ACTIVE → structure frozen, schedule actions allowed", () => {
    const mode = deriveAdminUiMode({
      contest: baseContest,
      round: activeRoundFarDeadline,
      deadlinePassed: false,
    });
    expect(mode.canEditRoundStructure).toBe(false);
    expect(mode.canEditMatchStatusAndDate).toBe(true);
  });

  it("[UNIT-UI-MODE-ACTIVE] ACTIVE + deadlinePassed → effective CLOSED, schedule frozen", () => {
    const mode = deriveAdminUiMode({
      contest: baseContest,
      round: activeRoundFarDeadline,
      deadlinePassed: true,
    });
    expect(mode.canEditRoundStructure).toBe(false);
    expect(mode.canEditMatchStatusAndDate).toBe(false);
    expect(mode.showDeadlinePassedHint).toBe(true);
  });

  it("allows structure edit in DRAFT", () => {
    const draft = deriveAdminUiMode({ contest: baseContest, round: draftRound });
    expect(draft.canEditRoundStructure).toBe(true);
    expect(draft.canEditMatchStatusAndDate).toBe(true);
  });

  it("[UNIT-DEADLINE-LOCKOUT] ACTIVE + near deadline → canChangeDeadline false", () => {
    const mode = deriveAdminUiMode({
      contest: baseContest,
      round: activeRoundNearDeadline,
      deadlinePassed: false,
    });
    expect(mode.canChangeDeadline).toBe(false);
    expect(mode.canEditDeadline).toBe(false);
  });

  it("[UNIT-DEADLINE-LOCKOUT] ACTIVE + far deadline → canChangeDeadline true", () => {
    const mode = deriveAdminUiMode({
      contest: baseContest,
      round: activeRoundFarDeadline,
      deadlinePassed: false,
    });
    expect(mode.canChangeDeadline).toBe(true);
    expect(mode.canEditDeadline).toBe(true);
  });

  it("[UNIT-UI-MODE-RESULTS-CLOSED] CLOSED → canEnterResults, canCalculate, !canPublish", () => {
    const closed: RoundOut = { ...draftRound, status: "CLOSED" };
    const mode = deriveAdminUiMode({ contest: baseContest, round: closed });
    expect(mode.canEnterResults).toBe(true);
    expect(mode.canCalculate).toBe(true);
    expect(mode.canPublish).toBe(false);
    expect(mode.resultsReadonly).toBe(false);
  });

  it("[API-RESULT-CALCULATED] CALCULATED → canEnterResults true, resultsReadonly false", () => {
    const calculated: RoundOut = { ...draftRound, status: "CALCULATED" };
    const mode = deriveAdminUiMode({ contest: baseContest, round: calculated });
    expect(mode.canEnterResults).toBe(true);
    expect(mode.resultsReadonly).toBe(false);
    expect(mode.canPublish).toBe(true);
    expect(mode.canCalculate).toBe(false);
  });

  it("[UNIT-UI-MODE-RESULTS-CLOSED] PUBLISHED → resultsReadonly, !canCalculate, !canPublish", () => {
    const mode = deriveAdminUiMode({ contest: baseContest, round: publishedRound });
    expect(mode.showAppliedBadge).toBe(true);
    expect(mode.resultsReadonly).toBe(true);
    expect(mode.canCalculate).toBe(false);
    expect(mode.canPublish).toBe(false);
    expect(mode.canVoidMatch).toBe(true);
  });

  it("allows results entry when ACTIVE round deadline passed (effective CLOSED)", () => {
    const mode = deriveAdminUiMode({
      contest: baseContest,
      round: activeRoundFarDeadline,
      deadlinePassed: true,
    });
    expect(mode.canEnterResults).toBe(true);
    expect(mode.canCalculate).toBe(true);
  });

  it("allows create round when no draft exists", () => {
    const mode = deriveAdminUiMode({
      contest: baseContest,
      round: activeRoundFarDeadline,
      hasDraftRound: false,
    });
    expect(mode.canCreateRound).toBe(true);
  });

  it("blocks create round when draft already exists", () => {
    const mode = deriveAdminUiMode({
      contest: baseContest,
      round: activeRoundFarDeadline,
      hasDraftRound: true,
    });
    expect(mode.canCreateRound).toBe(false);
  });

  it("[UNIT-UI-MODE-RESULTS-CLOSED] PAUSED contest overrides mutations", () => {
    const closed: RoundOut = { ...draftRound, status: "CLOSED" };
    const mode = deriveAdminUiMode({
      contest: { ...baseContest, status: "PAUSED" },
      round: closed,
    });
    expect(mode.disableAllMutations).toBe(true);
    expect(mode.canEnterResults).toBe(false);
    expect(mode.canCalculate).toBe(false);
    expect(mode.canPublish).toBe(false);
    expect(mode.canVoidMatch).toBe(false);
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
