"use client";

import { PrivacyMask } from "@/components/predictions/PrivacyMask";
import { OutcomeStatsFooter } from "@/components/predictions/OutcomeStatsFooter";
import { TeamColumnHeader } from "@/components/predictions/TeamColumnHeader";
import { formatPredictionScore } from "@/lib/privacy/formatPredictionCell";
import { shouldShowScore } from "@/lib/privacy/shouldShowScore";
import { adaptiveNameClass, COL_NAME } from "@/lib/table/columnStyles";
import type { MatchOut, PredictionEntryOut, UserOut } from "@/types/api";

interface PredictionsMatrixProps {
  matches: MatchOut[];
  entries: PredictionEntryOut[];
  deadlinePassed: boolean;
  viewer: UserOut | null;
  roundTitle: string;
  showStats?: boolean;
}

function ScoreCell({ score1, score2 }: { score1: number; score2: number }) {
  return (
    <span
      className="inline-block border border-gray-200 rounded px-1 py-0.5 text-sm bg-white tabular-nums"
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
  showStats = false,
}: PredictionsMatrixProps) {
  return (
    <div className="overflow-x-auto" data-testid="predictions-matrix">
      <table className="border border-gray-200 rounded-lg text-base w-max max-w-full">
        <thead>
          <tr className="bg-gray-50">
            <th className="px-2 py-2 text-left font-medium text-gray-700 border-b sticky left-0 bg-gray-50 z-10">
              Счет
            </th>
            {matches.map((m) => (
              <th
                key={m.id}
                className="px-1 py-1.5 text-center font-medium text-gray-700 border-b min-w-[4.5rem]"
              >
                <TeamColumnHeader team1={m.team1} team2={m.team2} size="normal" />
              </th>
            ))}
          </tr>
          <tr className="bg-gray-50">
            <th className="px-2 py-1.5 text-left text-gray-500 border-b sticky left-0 bg-gray-50">
              {roundTitle}
            </th>
            {matches.map((m) => (
              <th key={`sub-${m.id}`} className="border-b min-w-[4.5rem]" />
            ))}
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => {
            const name = entry.user_name ?? `Участник ${entry.user_id}`;
            return (
              <tr key={entry.user_id} className="border-b border-gray-100">
                <td
                  className={`${COL_NAME} font-medium text-gray-900 bg-white ${adaptiveNameClass(name)}`}
                >
                  {name}
                </td>
                {matches.map((m) => {
                  const pred = entry.predictions?.find((p) => p.match_id === m.id);
                  const show = shouldShowScore(entry, viewer, deadlinePassed);

                  return (
                    <td key={m.id} className="px-1 py-1.5 text-center min-w-[4.5rem]">
                      {show && pred && pred.score1 != null && pred.score2 != null ? (
                        <ScoreCell score1={pred.score1} score2={pred.score2} />
                      ) : entry.submitted && entry.predictions === null ? (
                        <PrivacyMask />
                      ) : show && pred ? (
                        <span className="text-gray-400 text-sm">{formatPredictionScore(pred)}</span>
                      ) : (
                        <span className="text-gray-400 text-sm">—</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
        {showStats && (
          <tfoot>
            <OutcomeStatsFooter matches={matches} entries={entries} />
          </tfoot>
        )}
      </table>
    </div>
  );
}
