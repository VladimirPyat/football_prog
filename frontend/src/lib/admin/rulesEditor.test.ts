import { describe, expect, it } from "vitest";
import { buildRulesJsonPatch, formStateToRulesJson, rulesJsonToFormState } from "@/lib/admin/rulesEditor";

const sampleRules = {
  scoring_rules: {
    base_points: {
      exact_high_score: 16,
      exact_score: 12,
      diff_plus_outcome: 8,
      outcome_only: 4,
      miss: 0,
    },
    bonuses: {
      bonus_1_unique_multiplier_pct: 200,
      bonus_2_thresholds: [
        { min_correct_outcomes: 6, points: 8 },
        { min_correct_outcomes: 7, points: 12 },
      ],
      bonus_3_rank_points: { "1st": 12, "2nd": 8, "3rd": 4 },
      bonus_3_base_threshold_extra: 50,
      bonus_3_extra_points: 4,
    },
  },
  tiebreakers: {},
  constraints: {},
  contest_structure: {},
};

describe("rulesEditor", () => {
  it("round-trips base points and bonuses", () => {
    const form = rulesJsonToFormState(sampleRules);
    form.basePoints.exact_score = 10;
    form.bonus3Rank.first = 15;
    const patched = formStateToRulesJson(sampleRules, form);
    const scoring = patched.scoring_rules as Record<string, unknown>;
    const base = scoring.base_points as Record<string, number>;
    const bonuses = scoring.bonuses as Record<string, unknown>;
    const rank = bonuses.bonus_3_rank_points as Record<string, number>;
    expect(base.exact_score).toBe(10);
    expect(rank["1st"]).toBe(15);
  });

  it("mirrors structure columns into rules_json.contest_structure", () => {
    const form = rulesJsonToFormState(sampleRules);
    const patched = buildRulesJsonPatch(sampleRules, form, {
      total_teams: 20,
      matches_per_round: 10,
      total_rounds: 38,
      is_round_robin: true,
    });
    const cs = patched.contest_structure as Record<string, unknown>;
    expect(cs.total_teams).toBe(20);
    expect(cs.matches_per_round).toBe(10);
  });
});
