"use client";

import { formatDateTimeRu } from "@/lib/datetime/formatApiDateTime";
import { ScoreInput } from "@/components/predictions/ScoreInput";
import { shortenTeamLabel } from "@/lib/teams/formatTeamPair";
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
  const homeShort = shortenTeamLabel(match.team1, 4);
  const awayShort = shortenTeamLabel(match.team2, 4);

  return (
    <div className="flex flex-col sm:flex-row sm:items-start gap-2 sm:gap-4 py-3 border-b border-gray-100 last:border-0">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900">
          {match.team1} — {match.team2}
        </p>
        <p className="text-xs text-gray-500">{formatDateTimeRu(match.date_time)}</p>
      </div>
      <div className="flex items-start gap-1 sm:gap-2 shrink-0">
        <span
          className="text-xs sm:text-sm text-gray-700 hidden sm:inline w-10 text-right pt-1.5 shrink-0"
          title={match.team1}
        >
          {homeShort}
        </span>
        <ScoreInput
          value={score1}
          onChange={onScore1Change}
          maxScore={maxScore}
          disabled={readonly}
          aria-label={`Счёт ${match.team1}`}
        />
        <span className="text-gray-500 pt-1.5 shrink-0">:</span>
        <ScoreInput
          value={score2}
          onChange={onScore2Change}
          maxScore={maxScore}
          disabled={readonly}
          aria-label={`Счёт ${match.team2}`}
        />
        <span
          className="text-xs sm:text-sm text-gray-700 hidden sm:inline w-10 pt-1.5 shrink-0"
          title={match.team2}
        >
          {awayShort}
        </span>
      </div>
    </div>
  );
}
