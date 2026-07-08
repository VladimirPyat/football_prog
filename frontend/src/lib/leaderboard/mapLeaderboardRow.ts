import type { LeaderboardEntryOut } from "@/types/api";

export interface LeaderboardTableRow {
  rank: number;
  user_name: string;
  predictions_count: number;
  count_exact_high: number;
  count_exact: number;
  count_diff: number;
  count_outcome: number;
  bonus1: number;
  bonus2: number;
  bonus3: number;
  points_base: number;
  total_bonus_points: number;
  total_with_bonus3: number;
}

const COUNT_FIELDS = ["count_exact_high", "count_exact", "count_diff", "count_outcome"] as const;

export function mapLeaderboardRow(row: LeaderboardEntryOut): LeaderboardTableRow {
  const totalBonus =
    row.total_bonus_points ?? row.bonus1 + row.bonus2 + row.bonus3;
  return {
    rank: row.rank,
    user_name: row.user_name,
    predictions_count: row.predictions_count,
    count_exact_high: row.count_exact_high ?? 0,
    count_exact: row.count_exact ?? 0,
    count_diff: row.count_diff ?? 0,
    count_outcome: row.count_outcome ?? 0,
    bonus1: row.bonus1,
    bonus2: row.bonus2,
    bonus3: row.bonus3,
    points_base: row.points_base,
    total_bonus_points: totalBonus,
    total_with_bonus3: row.total_with_bonus3,
  };
}

export function mapLeaderboardRows(rows: LeaderboardEntryOut[]): LeaderboardTableRow[] {
  return rows.map(mapLeaderboardRow);
}

/** True when API returned B4 count_* fields on at least one row. */
export function hasLeaderboardCountColumns(rows: LeaderboardEntryOut[]): boolean {
  if (rows.length === 0) return true;
  return COUNT_FIELDS.every((field) => rows[0][field] !== undefined);
}

export function warnIfMissingCountColumns(rows: LeaderboardEntryOut[]): boolean {
  const hasColumns = hasLeaderboardCountColumns(rows);
  if (!hasColumns && rows.length > 0) {
    console.warn(
      "[LeaderboardTable] count_* fields missing from API response; hiding count columns",
    );
  }
  return hasColumns;
}
