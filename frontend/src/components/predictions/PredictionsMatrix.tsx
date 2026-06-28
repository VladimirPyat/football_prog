"use client";

import { PrivacyMask } from "@/components/predictions/PrivacyMask";
import { formatPredictionScore } from "@/lib/privacy/formatPredictionCell";
import { shouldShowScore } from "@/lib/privacy/shouldShowScore";
import type { MatchOut, PredictionEntryOut, UserOut } from "@/types/api";

interface PredictionsMatrixProps {
  matches: MatchOut[];
  entries: PredictionEntryOut[];
  deadlinePassed: boolean;
  viewer: UserOut | null;
  roundTitle: string;
}

function ScoreCell({ score1, score2 }: { score1: number; score2: number }) {
  return (
    <span
      className="inline-block border border-gray-200 rounded px-2 py-0.5 text-sm bg-white"
      data-testid="prediction-score"
    >
      {score1}:{score2}
    </span>
  );
}

export function PredictionsMatrix({
  matches,
  entries,
  deadlinePassed,
  viewer,
  roundTitle,
}: PredictionsMatrixProps) {
  return (
    <div className="overflow-x-auto" data-testid="predictions-matrix">
      <table className="min-w-full border border-gray-200 rounded-lg text-sm">
        <thead>
          <tr className="bg-gray-50">
            <th className="px-3 py-2 text-left font-medium text-gray-700 border-b">Счет</th>
            {matches.map((m) => (
              <th
                key={m.id}
                className="px-3 py-2 text-center font-medium text-gray-700 border-b whitespace-nowrap"
              >
                <div>
                  {m.team1}-{m.team2}
                </div>
              </th>
            ))}
          </tr>
          <tr className="bg-gray-50">
            <th className="px-3 py-2 text-left text-gray-500 border-b text-xs">{roundTitle}</th>
            {matches.map((m) => (
              <th key={`sub-${m.id}`} className="border-b" />
            ))}
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <tr key={entry.user_id} className="border-b border-gray-100">
              <td className="px-3 py-2 font-medium text-gray-900 whitespace-nowrap">
                {entry.user_name ?? `Участник ${entry.user_id}`}
              </td>
              {matches.map((m) => {
                const pred = entry.predictions?.find((p) => p.match_id === m.id);
                const show = shouldShowScore(entry, viewer, deadlinePassed);

                return (
                  <td key={m.id} className="px-3 py-2 text-center">
                    {show && pred && pred.score1 != null && pred.score2 != null ? (
                      <ScoreCell score1={pred.score1} score2={pred.score2} />
                    ) : entry.submitted && entry.predictions === null ? (
                      <PrivacyMask />
                    ) : show && pred ? (
                      <span className="text-gray-400">{formatPredictionScore(pred)}</span>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
