"use client";

import Link from "next/link";
import {
  formatDateTimeRu,
  matchPhaseLabel,
  matchStatusLabel,
  roundStatusHint,
} from "@/lib/admin/format";
import { AdminTable, AdminTh } from "@/components/ui/AdminTable";
import { Button } from "@/components/ui/Button";
import { Callout } from "@/components/ui/Callout";
import { TD_ADMIN, TR_ADMIN_BORDER } from "@/lib/table/tableHeaderStyles";
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
    <AdminTable
      headers={
        <>
          <AdminTh>Матч</AdminTh>
          <AdminTh>Дата</AdminTh>
          <AdminTh>Статус</AdminTh>
          {showScores && <AdminTh>Счёт</AdminTh>}
        </>
      }
    >
      {matches.map((m) => (
        <tr key={m.id} className={TR_ADMIN_BORDER}>
          <td className={TD_ADMIN}>
            {m.team1} — {m.team2}
          </td>
          <td className={TD_ADMIN}>{formatDateTimeRu(m.date_time)}</td>
          <td className={TD_ADMIN}>
            {usePhaseLabel
              ? matchPhaseLabel(m.status, m.date_time, round.status)
              : matchStatusLabel(m.status)}
          </td>
          {showScores && <td className={TD_ADMIN}>{formatScore(m)}</td>}
        </tr>
      ))}
    </AdminTable>
  );
}

function GoToResultsLink({ roundId, contestId }: { roundId: number; contestId: number }) {
  return (
    <Link href={`/admin/results?round=${roundId}&contest=${contestId}`}>
      <Button size="md">Перейти к результатам</Button>
    </Link>
  );
}

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
      <Callout variant="warning">{roundStatusHint("CLOSED")}</Callout>
      <MatchTable matches={matches} round={round} showScores />
      <GoToResultsLink roundId={round.id} contestId={contestId} />
    </div>
  );
}

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
      <Callout variant="info">{roundStatusHint("CALCULATED")}</Callout>
      <MatchTable matches={matches} round={round} showScores />
      <GoToResultsLink roundId={round.id} contestId={contestId} />
    </div>
  );
}

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
      <Callout variant="info">{roundStatusHint("PUBLISHED")}</Callout>
      <MatchTable matches={matches} round={round} showScores />
      <GoToResultsLink roundId={round.id} contestId={contestId} />
    </div>
  );
}

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
