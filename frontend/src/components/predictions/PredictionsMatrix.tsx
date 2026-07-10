"use client";

import { PrivacyMask } from "@/components/predictions/PrivacyMask";
import { OutcomeStatsFooter } from "@/components/predictions/OutcomeStatsFooter";
import { TeamColumnHeader } from "@/components/predictions/TeamColumnHeader";
import { DataTable } from "@/components/ui/DataTable";
import { formatPredictionScore } from "@/lib/privacy/formatPredictionCell";
import { shouldShowScore } from "@/lib/privacy/shouldShowScore";
import { adaptiveNameClass, COL_DIGIT2, COL_NAME } from "@/lib/table/columnStyles";
import { headerLabel } from "@/lib/table/headerLabel";
import { TH_GROUP, TH_STICKY } from "@/lib/table/tableHeaderStyles";
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

const MATCH_COL = `${COL_DIGIT2} min-w-[3.25rem]`;

export function PredictionsMatrix({
  matches,
  entries,
  deadlinePassed,
  viewer,
  roundTitle,
  showStats = false,
}: PredictionsMatrixProps) {
  return (
    <DataTable testId="predictions-matrix">
      <thead>
        <tr className="bg-gray-50">
          <th className={`${TH_STICKY} left-0 ${COL_NAME} text-left`}>
            {headerLabel(["Счёт"])}
          </th>
          {matches.map((m) => (
            <th key={m.id} className={`${TH_GROUP} ${MATCH_COL} px-0.5 py-1.5`}>
              <TeamColumnHeader
                team1={m.team1}
                team2={m.team2}
                team1Short={m.team1_short}
                team2Short={m.team2_short}
                size="normal"
              />
            </th>
          ))}
        </tr>
        <tr className="bg-gray-50 text-sm text-gray-500">
          <th className={`${TH_STICKY} left-0 ${COL_NAME} text-left border-b font-normal`}>
            {roundTitle}
          </th>
          {matches.map((m) => (
            <th key={`sub-${m.id}`} className={`${MATCH_COL} border-b`} />
          ))}
        </tr>
      </thead>
      <tbody>
        {entries.map((entry) => {
          const name = entry.user_name ?? `Участник ${entry.user_id}`;
          return (
            <tr key={entry.user_id} className="border-b border-gray-100">
              <td
                className={`${COL_NAME} font-medium text-gray-900 bg-white sticky left-0 ${adaptiveNameClass(name)}`}
              >
                {name}
              </td>
              {matches.map((m) => {
                const pred = entry.predictions?.find((p) => p.match_id === m.id);
                const show = shouldShowScore(entry, viewer, deadlinePassed);

                return (
                  <td key={m.id} className={`${MATCH_COL} text-center`}>
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
    </DataTable>
  );
}
