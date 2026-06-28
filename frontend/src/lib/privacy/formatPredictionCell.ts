import type { MatchPredictionOut } from "@/types/api";

export function formatPredictionScore(pred: MatchPredictionOut | undefined): string {
  if (!pred || pred.score1 == null || pred.score2 == null) return "—";
  return `${pred.score1}:${pred.score2}`;
}
