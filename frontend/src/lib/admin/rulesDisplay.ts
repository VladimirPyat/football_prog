export interface RulesDisplayRow {
  label: string;
  value: string;
}

export interface RulesDisplaySections {
  structure: RulesDisplayRow[];
  basePoints: RulesDisplayRow[];
  bonuses: RulesDisplayRow[];
}

const BASE_POINT_LABELS: Record<string, string> = {
  exact_high_score: "За предсказанный крупный счёт",
  exact_score: "За точный счёт",
  diff_plus_outcome: "За правильную разницу мячей",
  outcome_only: "За правильный исход",
  miss: "За промах",
};

function formatBonus2Thresholds(thresholds: unknown): string {
  if (!Array.isArray(thresholds)) return String(thresholds ?? "—");
  return thresholds
    .map((row) => {
      const t = row as { min_correct_outcomes?: number; points?: number };
      return `${t.min_correct_outcomes ?? "?"} → ${t.points ?? "?"} очк.`;
    })
    .join("; ");
}

function formatRankPoints(rankPoints: unknown): string {
  if (!rankPoints || typeof rankPoints !== "object") return String(rankPoints ?? "—");
  const rp = rankPoints as Record<string, number>;
  return Object.entries(rp)
    .map(([place, pts]) => `${place}: ${pts}`)
    .join(", ");
}

/** Parse contest.rules_json into labeled sections for supervisor parameters UI. */
export function parseRulesForDisplay(rulesJson: Record<string, unknown>): RulesDisplaySections {
  const structure = (rulesJson.contest_structure as Record<string, unknown>) ?? {};
  const scoringRules = (rulesJson.scoring_rules as Record<string, unknown>) ?? {};
  const basePoints = (scoringRules.base_points as Record<string, unknown>) ?? {};
  const bonuses = (scoringRules.bonuses as Record<string, unknown>) ?? {};

  const structureRows: RulesDisplayRow[] = [];
  if (structure.deadline_rule_hours != null) {
    structureRows.push({
      label: "Правило дедлайна (ч)",
      value: String(structure.deadline_rule_hours),
    });
  }
  if (structure.max_score_value != null) {
    structureRows.push({
      label: "Макс. значение счёта",
      value: String(structure.max_score_value),
    });
  }

  const baseRows: RulesDisplayRow[] = Object.entries(BASE_POINT_LABELS).map(([key, label]) => ({
    label,
    value: basePoints[key] != null ? String(basePoints[key]) : "—",
  }));

  const bonusRows: RulesDisplayRow[] = [];
  if (bonuses.bonus_1_unique_multiplier_pct != null) {
    bonusRows.push({
      label: "Бонус 1: Уникальный прогноз (%)",
      value: String(bonuses.bonus_1_unique_multiplier_pct),
    });
  }
  if (bonuses.bonus_2_thresholds != null) {
    bonusRows.push({
      label: "Бонус 2: Угадано N матчей",
      value: formatBonus2Thresholds(bonuses.bonus_2_thresholds),
    });
  }
  if (bonuses.bonus_3_rank_points != null) {
    bonusRows.push({
      label: "Бонус 3: Топ-3 места в туре",
      value: formatRankPoints(bonuses.bonus_3_rank_points),
    });
  }
  if (bonuses.bonus_3_base_threshold_extra != null || bonuses.bonus_3_extra_points != null) {
    bonusRows.push({
      label: "Дополнительно (порог очков)",
      value: `от ${bonuses.bonus_3_base_threshold_extra ?? "?"} → +${bonuses.bonus_3_extra_points ?? "?"} очк.`,
    });
  }

  return {
    structure: structureRows,
    basePoints: baseRows,
    bonuses: bonusRows,
  };
}
