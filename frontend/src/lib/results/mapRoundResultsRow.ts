import type { MatchOut, RoundResultRowOut } from "@/types/api";

export interface ResultsMatrixMatch {
  id: number;
  team1: string;
  team2: string;
  team1_short?: string;
  team2_short?: string;
  score1: number | null;
  score2: number | null;
}

export interface ResultsMatrixRow {
  user_name: string;
  match_points: (number | null)[];
  bonus1: number | null;
  bonus2: number | null;
  bonus3: number | null;
  total_without_bonus: number;
  total: number;
}

export function mapResultsMatrixMatch(match: MatchOut): ResultsMatrixMatch {
  return {
    id: match.id,
    team1: match.team1,
    team2: match.team2,
    team1_short: match.team1_short,
    team2_short: match.team2_short,
    score1: match.score1,
    score2: match.score2,
  };
}

export function mapRoundResultsRow(row: RoundResultRowOut, matchIds: number[]): ResultsMatrixRow {
  const pointsByMatch = new Map(row.points.map((entry) => [entry.match_id, entry.base_points]));
  return {
    user_name: row.user_name,
    match_points: matchIds.map((matchId) => pointsByMatch.get(matchId) ?? null),
    bonus1: row.bonus1,
    bonus2: row.bonus2,
    bonus3: row.bonus3,
    total_without_bonus: row.total_without_bonus3,
    total: row.total,
  };
}

export function mapRoundResultsRows(
  rows: RoundResultRowOut[],
  matchIds: number[],
): ResultsMatrixRow[] {
  return rows.map((row) => mapRoundResultsRow(row, matchIds));
}

export function roundResultsPointsMissing(matches: MatchOut[], rows: RoundResultRowOut[]): boolean {
  if (matches.length === 0 || rows.length === 0) return false;
  return rows.every((row) => row.points.length === 0);
}
