import { z } from "zod";

export type MatchScoreState = { score1?: number; score2?: number };

/** Build POST payload only from matches with both explicit integer scores. */
export function buildPredictionBatch(
  form: Record<number, MatchScoreState>,
  matchIds: number[],
): { match_id: number; score1: number; score2: number }[] {
  return matchIds
    .map((matchId) => {
      const cell = form[matchId];
      if (cell?.score1 === undefined || cell?.score2 === undefined) return null;
      if (!Number.isInteger(cell.score1) || !Number.isInteger(cell.score2)) return null;
      return { match_id: matchId, score1: cell.score1, score2: cell.score2 };
    })
    .filter((item): item is { match_id: number; score1: number; score2: number } => item !== null);
}

export function countFilledMatches(
  form: Record<number, MatchScoreState>,
  matchIds: number[],
): number {
  return matchIds.filter((id) => {
    const cell = form[id];
    return (
      cell?.score1 !== undefined &&
      cell?.score2 !== undefined &&
      Number.isInteger(cell.score1) &&
      Number.isInteger(cell.score2)
    );
  }).length;
}

export function predictionBatchSchema(maxScore: number, matchCount: number) {
  const score = z.number().int().min(0).max(maxScore);
  return z.object({
    predictions: z
      .array(z.object({ match_id: z.number().int(), score1: score, score2: score }))
      .length(matchCount),
  });
}
