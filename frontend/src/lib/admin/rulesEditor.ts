export interface Bonus2Threshold {
  min_correct_outcomes: number;
  points: number;
}

export interface RulesFormState {
  basePoints: {
    exact_high_score: number;
    exact_score: number;
    diff_plus_outcome: number;
    outcome_only: number;
  };
  bonus1MultiplierPct: number;
  bonus2Thresholds: Bonus2Threshold[];
  bonus3Rank: { first: number; second: number; third: number };
  bonus3BaseThresholdExtra: number;
  bonus3ExtraPoints: number;
}

function asNumber(value: unknown, fallback: number): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

/** Map rules_json → flat form state for supervisor editor. */
export function rulesJsonToFormState(rulesJson: Record<string, unknown>): RulesFormState {
  const scoring = (rulesJson.scoring_rules as Record<string, unknown>) ?? {};
  const base = (scoring.base_points as Record<string, unknown>) ?? {};
  const bonuses = (scoring.bonuses as Record<string, unknown>) ?? {};
  const rank = (bonuses.bonus_3_rank_points as Record<string, number>) ?? {};

  const rawThresholds = bonuses.bonus_2_thresholds;
  const thresholds: Bonus2Threshold[] = Array.isArray(rawThresholds)
    ? rawThresholds.map((row) => {
        const t = row as Record<string, unknown>;
        return {
          min_correct_outcomes: asNumber(t.min_correct_outcomes, 0),
          points: asNumber(t.points, 0),
        };
      })
    : [
        { min_correct_outcomes: 6, points: 8 },
        { min_correct_outcomes: 7, points: 12 },
        { min_correct_outcomes: 8, points: 16 },
      ];

  return {
    basePoints: {
      exact_high_score: asNumber(base.exact_high_score, 16),
      exact_score: asNumber(base.exact_score, 12),
      diff_plus_outcome: asNumber(base.diff_plus_outcome, 8),
      outcome_only: asNumber(base.outcome_only, 4),
    },
    bonus1MultiplierPct: asNumber(bonuses.bonus_1_unique_multiplier_pct, 200),
    bonus2Thresholds: thresholds,
    bonus3Rank: {
      first: asNumber(rank["1st"], 12),
      second: asNumber(rank["2nd"], 8),
      third: asNumber(rank["3rd"], 4),
    },
    bonus3BaseThresholdExtra: asNumber(bonuses.bonus_3_base_threshold_extra, 50),
    bonus3ExtraPoints: asNumber(bonuses.bonus_3_extra_points, 4),
  };
}

/** Merge form state back into a copy of rules_json for PATCH. */
export function formStateToRulesJson(
  rulesJson: Record<string, unknown>,
  form: RulesFormState,
): Record<string, unknown> {
  const next = structuredClone(rulesJson) as Record<string, unknown>;
  const scoring = (next.scoring_rules as Record<string, unknown>) ?? {};
  const base = (scoring.base_points as Record<string, unknown>) ?? {};
  const bonuses = (scoring.bonuses as Record<string, unknown>) ?? {};

  base.exact_high_score = form.basePoints.exact_high_score;
  base.exact_score = form.basePoints.exact_score;
  base.diff_plus_outcome = form.basePoints.diff_plus_outcome;
  base.outcome_only = form.basePoints.outcome_only;
  base.miss = base.miss ?? 0;

  bonuses.bonus_1_unique_multiplier_pct = form.bonus1MultiplierPct;
  bonuses.bonus_2_thresholds = form.bonus2Thresholds.map((row) => ({
    min_correct_outcomes: row.min_correct_outcomes,
    points: row.points,
  }));
  bonuses.bonus_3_rank_points = {
    "1st": form.bonus3Rank.first,
    "2nd": form.bonus3Rank.second,
    "3rd": form.bonus3Rank.third,
  };
  bonuses.bonus_3_base_threshold_extra = form.bonus3BaseThresholdExtra;
  bonuses.bonus_3_extra_points = form.bonus3ExtraPoints;

  scoring.base_points = base;
  scoring.bonuses = bonuses;
  next.scoring_rules = scoring;
  return next;
}

export interface ContestStructurePatch {
  total_teams: number;
  matches_per_round: number;
  total_rounds: number;
  is_round_robin: boolean;
}

/** Full rules_json payload for PATCH — scoring + mirrored contest_structure columns. */
export function buildRulesJsonPatch(
  rulesJson: Record<string, unknown>,
  form: RulesFormState,
  structure: ContestStructurePatch,
): Record<string, unknown> {
  const next = formStateToRulesJson(rulesJson, form);
  const cs = ((next.contest_structure as Record<string, unknown>) ?? {}) as Record<string, unknown>;
  cs.total_teams = structure.total_teams;
  cs.matches_per_round = structure.matches_per_round;
  cs.total_rounds = structure.total_rounds;
  cs.is_round_robin = structure.is_round_robin;
  next.contest_structure = cs;
  return next;
}
