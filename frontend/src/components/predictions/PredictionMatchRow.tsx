"use client";

import { formatDateTimeRu } from "@/lib/datetime/formatApiDateTime";
import { ScoreInput } from "@/components/predictions/ScoreInput";
import type { MatchOut } from "@/types/api";

interface PredictionMatchRowProps {
  match: MatchOut;
  score1: number | "";
  score2: number | "";
  maxScore: number;
  readonly: boolean;
  onScore1Change: (v: number | "") => void;
  onScore2Change: (v: number | "") => void;
}

export function PredictionMatchRow({
  match,
  score1,
  score2,
  maxScore,
  readonly,
  onScore1Change,
  onScore2Change,
}: PredictionMatchRowProps) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 py-3 border-b border-gray-100 last:border-0">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900">
          {match.team1} — {match.team2}
        </p>
        <p className="text-xs text-gray-500">{formatDateTimeRu(match.date_time)}</p>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-700 hidden sm:inline">{match.team1}</span>
        <ScoreInput
          value={score1}
          onChange={onScore1Change}
          maxScore={maxScore}
          disabled={readonly}
          aria-label={`Счёт ${match.team1}`}
        />
        <span className="text-gray-500">:</span>
        <ScoreInput
          value={score2}
          onChange={onScore2Change}
          maxScore={maxScore}
          disabled={readonly}
          aria-label={`Счёт ${match.team2}`}
        />
        <span className="text-sm text-gray-700 hidden sm:inline">{match.team2}</span>
        <span className="text-xs text-gray-400 ml-1">0–{maxScore}</span>
      </div>
    </div>
  );
}
