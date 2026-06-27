"use client";

import Link from "next/link";
import { useState } from "react";
import { formatDateTimeRu, matchPhaseLabel, matchStatusLabel, roundStatusHint } from "@/lib/admin/format";
import type { ContestOut, MatchOut, RoundOut } from "@/types/api";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { RoundLeaderboardPreview } from "@/components/admin/RoundLeaderboardPreview";

interface RoundPhasePanelProps {
  contest: ContestOut;
  round: RoundOut;
  matches: MatchOut[];
  disableAllMutations: boolean;
  onPublish?: (roundId: number) => Promise<void>;
}

/** Stub modal for unimplemented actions (VOID, predictions view). */
function StubModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <ConfirmDialog
      open={open}
      title="Скоро"
      message="Будет реализовано в будущих версиях."
      confirmLabel="Закрыть"
      onConfirm={onClose}
      onCancel={onClose}
    />
  );
}

/** Panel for CLOSED round (§9.4): read-only match list + stub action buttons. */
function ClosedPanel({
  round,
  matches,
  contestId,
}: {
  round: RoundOut;
  matches: MatchOut[];
  contestId: number;
}) {
  const [stub, setStub] = useState<string | null>(null);
  const hint = roundStatusHint("CLOSED");

  return (
    <div className="space-y-4">
      <p className="text-sm text-orange-800 bg-orange-50 border border-orange-200 rounded px-3 py-2">
        {hint}
      </p>

      <div className="overflow-x-auto border border-gray-200 rounded-lg">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left">Матч</th>
              <th className="px-3 py-2 text-left">Дата</th>
              <th className="px-3 py-2 text-left">Статус</th>
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
                  {matchPhaseLabel(m.status, m.date_time, "CLOSED")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          onClick={() => setStub("predictions")}
          className="px-4 py-2 text-sm border border-gray-300 rounded hover:bg-gray-50"
        >
          Просмотр прогнозов участников
        </button>
        <Link
          href={`/admin/results?round=${round.id}&contest=${contestId}`}
          className="px-4 py-2 text-sm text-white bg-blue-600 rounded hover:bg-blue-700"
        >
          Ввод результатов матчей
        </Link>
      </div>

      <StubModal open={stub === "predictions"} onClose={() => setStub(null)} />
    </div>
  );
}

/** Panel for CALCULATED round (§9.5): leaderboard preview + publish CTA. */
function CalculatedPanel({
  round,
  contestId,
  disableAllMutations,
  onPublish,
}: {
  round: RoundOut;
  contestId: number;
  disableAllMutations: boolean;
  onPublish?: (roundId: number) => Promise<void>;
}) {
  const [working, setWorking] = useState(false);
  const hint = roundStatusHint("CALCULATED");

  return (
    <div className="space-y-4">
      <p className="text-sm text-blue-800 bg-blue-50 border border-blue-200 rounded px-3 py-2">
        {hint}
      </p>

      <RoundLeaderboardPreview contestId={contestId} roundId={round.id} />

      <div className="flex flex-wrap gap-3">
        {!disableAllMutations && onPublish && (
          <button
            type="button"
            disabled={working}
            onClick={async () => {
              setWorking(true);
              try {
                await onPublish(round.id);
              } finally {
                setWorking(false);
              }
            }}
            className="px-4 py-2 text-sm text-white bg-green-600 rounded hover:bg-green-700 disabled:opacity-50"
          >
            {working ? "Публикация…" : "Опубликовать"}
          </button>
        )}
        <Link
          href={`/admin/results?round=${round.id}&contest=${contestId}`}
          className="px-4 py-2 text-sm border border-gray-300 rounded hover:bg-gray-50"
        >
          Открыть на вкладке Результаты
        </Link>
      </div>
    </div>
  );
}

/** Panel for PUBLISHED round (§9.6): read-only + stub "Отменить". */
function PublishedPanel({ matches }: { matches: MatchOut[] }) {
  const [stubOpen, setStubOpen] = useState(false);
  const hint = roundStatusHint("PUBLISHED");

  return (
    <div className="space-y-4">
      <p className="text-sm text-purple-800 bg-purple-50 border border-purple-200 rounded px-3 py-2">
        {hint}
      </p>

      <div className="overflow-x-auto border border-gray-200 rounded-lg">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left">Матч</th>
              <th className="px-3 py-2 text-left">Дата</th>
              <th className="px-3 py-2 text-left">Статус</th>
            </tr>
          </thead>
          <tbody>
            {matches.map((m) => (
              <tr key={m.id} className="border-t border-gray-200">
                <td className="px-3 py-2">
                  {m.team1} — {m.team2}
                </td>
                <td className="px-3 py-2">{formatDateTimeRu(m.date_time)}</td>
                <td className="px-3 py-2">{matchStatusLabel(m.status)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <button
        type="button"
        onClick={() => setStubOpen(true)}
        className="px-4 py-2 text-sm border border-gray-300 rounded hover:bg-gray-50 text-red-600"
      >
        Отменить
      </button>

      <StubModal open={stubOpen} onClose={() => setStubOpen(false)} />
    </div>
  );
}

/**
 * Renders per-status content for CLOSED, CALCULATED, and PUBLISHED rounds on
 * the /admin/rounds page. DRAFT and ACTIVE are handled by RoundManagementPanel.
 */
export function RoundPhasePanel({
  contest,
  round,
  matches,
  disableAllMutations,
  onPublish,
}: RoundPhasePanelProps) {
  if (round.status === "CLOSED") {
    return <ClosedPanel round={round} matches={matches} contestId={contest.id} />;
  }
  if (round.status === "CALCULATED") {
    return (
      <CalculatedPanel
        round={round}
        contestId={contest.id}
        disableAllMutations={disableAllMutations}
        onPublish={onPublish}
      />
    );
  }
  if (round.status === "PUBLISHED") {
    return <PublishedPanel matches={matches} />;
  }
  return null;
}
