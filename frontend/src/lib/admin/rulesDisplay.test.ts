import { describe, it, expect } from "vitest";
import { parseRulesForDisplay } from "@/lib/admin/rulesDisplay";

const contestDefaultsFixture = {
  contest_structure: {
    deadline_rule_hours: 24,
    max_score_value: 20,
  },
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
      bonus_2_thresholds: [{ min_correct_outcomes: 6, points: 8 }],
      bonus_3_rank_points: { "1st": 12, "2nd": 8, "3rd": 4 },
      bonus_3_base_threshold_extra: 50,
      bonus_3_extra_points: 4,
    },
  },
};

describe("parseRulesForDisplay", () => {
  it("parses contest_defaults shape with Russian base point labels", () => {
    const sections = parseRulesForDisplay(contestDefaultsFixture);
    expect(sections.basePoints.length).toBeGreaterThan(0);
    expect(sections.bonuses.length).toBeGreaterThan(0);
    expect(sections.basePoints.find((r) => r.label.includes("точный счёт"))?.value).toBe("12");
    expect(sections.bonuses.some((r) => r.label.includes("Бонус 1"))).toBe(true);
    expect(sections.bonuses.some((r) => r.label.includes("Бонус 2"))).toBe(true);
  });
});
