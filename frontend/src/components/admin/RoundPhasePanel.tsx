"use client";

import Link from "next/link";
import {
  formatDateTimeRu,
  matchPhaseLabel,
  matchStatusLabel,
  roundStatusHint,
} from "@/lib/admin/format";
import type { ContestOut, MatchOut, RoundOut } from "@/types/api";

interface RoundPhasePanelProps {
  contest: ContestOut;
  round: RoundOut;
  matches: MatchOut[];
}

function formatScore(m: MatchOut): string {
  if (m.score1 != null && m.score2 != null) {
    return `${m.score1}:${m.score2}`;
  }
  return "—";
}

function MatchTable({
  matches,
  round,
  showScores,
}: {
  matches: MatchOut[];
  round: RoundOut;
  showScores: boolean;
}) {
  const usePhaseLabel = round.status === "CLOSED";

  return (
    <div className="overflow-x-auto border border-gray-200 rounded-lg">
      <table className="min-w-full text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-3 py-2 text-left">Матч</th>
            <th className="px-3 py-2 text-left">Дата</th>
            <th className="px-3 py-2 text-left">Статус</th>
            {showScores && <th className="px-3 py-2 text-left">Счёт</th>}
          </tr>
        </thead>
        <tbody>
          {matches.map((m) => (
            <tr key={m.id} className="border-t border-gray-200">
              <td className="px-3 py-2">
                {m.team1} — {m.team2}
              </td>
              <td className="px-3 py-2">{formatDateTimeRu(m.date_time)}</td>
              <td className="px-3 py-2">
                {usePhaseLabel
                  ? matchPhaseLabel(m.status, m.date_time, round.status)
                  : matchStatusLabel(m.status)}
              </td>
              {showScores && <td className="px-3 py-2">{formatScore(m)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function GoToResultsLink({ roundId, contestId }: { roundId: number; contestId: number }) {
  return (
    <Link
      href={`/admin/results?round=${roundId}&contest=${contestId}`}
      className="px-4 py-2 text-sm text-white bg-blue-600 rounded hover:bg-blue-700"
    >
      Перейти к результатам
    </Link>
  );
}

/** Panel for CLOSED round: read-only match list + CTA to Results tab. */
function ClosedPanel({
  round,
  matches,
  contestId,
}: {
  round: RoundOut;
  matches: MatchOut[];
  contestId: number;
}) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-orange-800 bg-orange-50 border border-orange-200 rounded px-3 py-2">
        {roundStatusHint("CLOSED")}
      </p>

      <MatchTable matches={matches} round={round} showScores />

      <GoToResultsLink roundId={round.id} contestId={contestId} />
    </div>
  );
}

/** Panel for CALCULATED round: match scores table, no participant LB. */
function CalculatedPanel({
  round,
  matches,
  contestId,
}: {
  round: RoundOut;
  matches: MatchOut[];
  contestId: number;
}) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-blue-800 bg-blue-50 border border-blue-200 rounded px-3 py-2">
        {roundStatusHint("CALCULATED")}
      </p>

      <MatchTable matches={matches} round={round} showScores />

      <GoToResultsLink roundId={round.id} contestId={contestId} />
    </div>
  );
}

/** Panel for PUBLISHED round: read-only match table + CTA. */
function PublishedPanel({
  round,
  matches,
  contestId,
}: {
  round: RoundOut;
  matches: MatchOut[];
  contestId: number;
}) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-purple-800 bg-purple-50 border border-purple-200 rounded px-3 py-2">
        {roundStatusHint("PUBLISHED")}
      </p>

      <MatchTable matches={matches} round={round} showScores />

      <GoToResultsLink roundId={round.id} contestId={contestId} />
    </div>
  );
}

/**
 * Renders per-status content for CLOSED, CALCULATED, and PUBLISHED rounds on
 * the /admin/rounds page. DRAFT and ACTIVE are handled by RoundManagementPanel.
 */
export function RoundPhasePanel({ contest, round, matches }: RoundPhasePanelProps) {
  if (round.status === "CLOSED") {
    return <ClosedPanel round={round} matches={matches} contestId={contest.id} />;
  }
  if (round.status === "CALCULATED") {
    return <CalculatedPanel round={round} matches={matches} contestId={contest.id} />;
  }
  if (round.status === "PUBLISHED") {
    return <PublishedPanel round={round} matches={matches} contestId={contest.id} />;
  }
  return null;
}
