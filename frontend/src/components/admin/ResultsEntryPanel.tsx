"use client";

import { useEffect, useState } from "react";
import { deriveAdminUiMode } from "@/lib/admin/deriveAdminUiMode";
import { formatRoundOptionLabel } from "@/lib/admin/roundLabel";
import { effectiveRoundStatus, isDeadlinePassedNow } from "@/lib/admin/roundEffectiveStatus";
import {
  BONUSES_PENDING_FALLBACK_MESSAGE,
  roundHasVisiblePostponements,
} from "@/lib/admin/roundScoringPending";
import { roundStatusHint } from "@/lib/admin/format";
import type { ContestOut, MatchOut, RoundOut } from "@/types/api";
import { MatchResultRow } from "@/components/admin/MatchResultRow";
import { RoundLeaderboardPreview } from "@/components/admin/RoundLeaderboardPreview";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { LoadingState } from "@/components/ui/LoadingState";
import { apiGet } from "@/lib/api/client";
import { contestAdmin } from "@/lib/api/endpoints";

interface ResultsEntryPanelProps {
  contest: ContestOut;
  maxScore: number;
  rounds: RoundOut[];
  selectedRoundId: number | null;
  matches: MatchOut[];
  loading: boolean;
  activeRoundId: number | null;
  activeDeadlinePassed: boolean;
  onSelectRound: (id: number) => void;
  onSaveResult: (matchId: number, score1: number, score2: number) => Promise<void>;
  onVoid: (matchId: number) => Promise<void>;
  onCalculate: (roundId: number) => Promise<void>;
  onPublish: (roundId: number) => Promise<void>;
}

function resultsStatusHint(roundStatus: string): string {
  switch (roundStatus) {
    case "CLOSED":
      return "Проверьте счета перед «Рассчитать».";
    case "CALCULATED":
      return "Можно исправить счёт — очки пересчитаются автоматически. После «Опубликовать» правка недоступна.";
    case "PUBLISHED":
      return "Тур опубликован. Счета и таблица зафиксированы.";
    default:
      return "";
  }
}

export function ResultsEntryPanel({
  contest,
  maxScore,
  rounds,
  selectedRoundId,
  matches,
  loading,
  activeRoundId,
  activeDeadlinePassed,
  onSelectRound,
  onSaveResult,
  onVoid,
  onCalculate,
  onPublish,
}: ResultsEntryPanelProps) {
  const selectedRound = rounds.find((r) => r.id === selectedRoundId) ?? null;
  const displayRoundStatus = selectedRound ? effectiveRoundStatus(selectedRound) : null;
  const uiMode = deriveAdminUiMode({
    contest,
    round: selectedRound,
    matches,
  });
  const [voidId, setVoidId] = useState<number | null>(null);
  const [working, setWorking] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [publishedStubOpen, setPublishedStubOpen] = useState(false);
  const [bonusesPendingMessage, setBonusesPendingMessage] = useState<string | null>(null);

  const eligibleRounds = rounds.filter(
    (r) =>
      ["CLOSED", "CALCULATED", "PUBLISHED"].includes(r.status) ||
      (r.status === "ACTIVE" && isDeadlinePassedNow(r.deadline)),
  );

  const allFinished = matches.every(
    (m) => m.status === "FINISHED" || m.status === "VOID" || m.status === "CANCELED",
  );

  const showBonusesPendingNote =
    roundHasVisiblePostponements(matches) || bonusesPendingMessage != null;

  useEffect(() => {
    if (!selectedRoundId || !selectedRound) {
      setBonusesPendingMessage(null);
      return;
    }
    if (!["CALCULATED", "PUBLISHED"].includes(selectedRound.status)) {
      setBonusesPendingMessage(null);
      return;
    }
    let cancelled = false;
    void apiGet<{ bonuses_pending?: boolean; bonuses_pending_message?: string | null }>(
      contestAdmin.rounds.leaderboard(contest.id, selectedRoundId),
    )
      .then((data) => {
        if (cancelled) return;
        setBonusesPendingMessage(
          data.bonuses_pending
            ? (data.bonuses_pending_message ?? BONUSES_PENDING_FALLBACK_MESSAGE)
            : null,
        );
      })
      .catch(() => {
        if (!cancelled) setBonusesPendingMessage(null);
      });
    return () => {
      cancelled = true;
    };
  }, [contest.id, selectedRoundId, selectedRound]);

  if (loading && !rounds.length) return <LoadingState message="Загрузка…" />;

  return (
    <div className="space-y-6">
      {eligibleRounds.length === 0 && (
        <p className="text-sm text-gray-600 bg-gray-50 border border-gray-200 rounded px-4 py-3">
          Нет туров, готовых к вводу результатов. Дождитесь окончания дедлайна активного тура.
        </p>
      )}

      {activeRoundId != null && activeDeadlinePassed && eligibleRounds.length === 0 && (
        <p className="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded px-4 py-3">
          Дедлайн прогнозов прошёл. Прогнозы закрыты; ввод результатов — на этой вкладке после
          обновления списка туров.
        </p>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <label className="text-sm text-gray-700">Тур:</label>
        <select
          value={selectedRoundId ?? ""}
          onChange={(e) => onSelectRound(Number(e.target.value))}
          className="border border-gray-300 rounded px-3 py-1 text-sm"
        >
          <option value="">Выберите тур</option>
          {eligibleRounds.map((r) => (
            <option key={r.id} value={r.id}>
              {formatRoundOptionLabel(r)}
            </option>
          ))}
        </select>
        {selectedRound && uiMode.showAppliedBadge && (
          <span className="text-sm font-medium text-green-700 bg-green-50 px-2 py-1 rounded">
            Применено
          </span>
        )}
      </div>

      {selectedRound && (
        <>
          <p className="text-sm text-gray-600 bg-gray-50 border border-gray-200 rounded px-3 py-2">
            {roundStatusHint(displayRoundStatus ?? selectedRound.status)}
          </p>

          <p className="text-sm text-gray-600">
            {resultsStatusHint(displayRoundStatus ?? selectedRound.status)}
          </p>

          {showBonusesPendingNote && (
            <p className="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded px-3 py-2">
              {bonusesPendingMessage ?? BONUSES_PENDING_FALLBACK_MESSAGE}
            </p>
          )}

          {displayRoundStatus === "CLOSED" && (
            <p className="text-sm text-blue-700 bg-blue-50 border border-blue-200 rounded px-3 py-2">
              Счёт можно вносить после времени начала каждого матча.
            </p>
          )}

          <div className="overflow-x-auto border border-gray-200 rounded-lg">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left">Матч</th>
                  <th className="px-3 py-2 text-left">Дата</th>
                  <th className="px-3 py-2 text-left">Статус</th>
                  <th className="px-3 py-2 text-left">Счёт</th>
                  <th className="px-3 py-2 text-left">Действия</th>
                </tr>
              </thead>
              <tbody>
                {matches.map((m) => (
                  <MatchResultRow
                    key={m.id}
                    match={m}
                    roundStatus={displayRoundStatus ?? selectedRound.status}
                    maxScore={maxScore}
                    scoresReadonly={uiMode.resultsReadonly || !uiMode.canEnterResults}
                    canVoid={uiMode.canVoidMatch && m.status !== "VOID"}
                    onSave={onSaveResult}
                    onVoid={(id) => setVoidId(id)}
                  />
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex flex-wrap gap-3">
            {uiMode.canCalculate && allFinished && (
              <button
                type="button"
                disabled={working}
                onClick={async () => {
                  setWorking(true);
                  try {
                    await onCalculate(selectedRound.id);
                  } finally {
                    setWorking(false);
                  }
                }}
                className="px-4 py-2 text-sm text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50"
              >
                Рассчитать
              </button>
            )}
            {uiMode.canPublish && (
              <button
                type="button"
                disabled={working}
                onClick={async () => {
                  setWorking(true);
                  try {
                    await onPublish(selectedRound.id);
                  } finally {
                    setWorking(false);
                  }
                }}
                className="px-4 py-2 text-sm text-white bg-green-600 rounded hover:bg-green-700 disabled:opacity-50"
              >
                Опубликовать
              </button>
            )}
            {selectedRound.status === "CALCULATED" && (
              <button
                type="button"
                onClick={() => setPreviewOpen(true)}
                className="px-4 py-2 text-sm border border-gray-300 rounded hover:bg-gray-50"
              >
                Результаты участников
              </button>
            )}
            {displayRoundStatus === "CLOSED" && (
              <span
                title="Сначала рассчитайте тур"
                className="px-4 py-2 text-sm border border-gray-200 rounded text-gray-400 cursor-not-allowed"
              >
                Результаты участников
              </span>
            )}
            {selectedRound.status === "PUBLISHED" && (
              <button
                type="button"
                onClick={() => setPublishedStubOpen(true)}
                className="px-4 py-2 text-sm border border-gray-300 rounded hover:bg-gray-50"
              >
                Результаты участников
              </button>
            )}
          </div>
        </>
      )}

      {previewOpen && selectedRound && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="lb-preview-title"
        >
          <div className="bg-white rounded-lg shadow-lg max-w-lg w-full max-h-[80vh] overflow-y-auto p-6 space-y-4">
            <div className="flex justify-between items-center">
              <h3 id="lb-preview-title" className="text-lg font-semibold">
                Результаты участников — тур {selectedRound.number}
              </h3>
              <button
                type="button"
                onClick={() => setPreviewOpen(false)}
                className="text-gray-500 hover:text-gray-700 text-xl leading-none"
                aria-label="Закрыть"
              >
                ×
              </button>
            </div>
            <RoundLeaderboardPreview contestId={contest.id} roundId={selectedRound.id} />
            <button
              type="button"
              onClick={() => setPreviewOpen(false)}
              className="px-4 py-2 text-sm border border-gray-300 rounded hover:bg-gray-50"
            >
              Закрыть
            </button>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={publishedStubOpen}
        title="Результаты участников"
        message="Полная матрица прогнозов — в следующих версиях."
        confirmLabel="Закрыть"
        onConfirm={() => setPublishedStubOpen(false)}
        onCancel={() => setPublishedStubOpen(false)}
      />

      <ConfirmDialog
        open={voidId !== null}
        title="Отменить матч (VOID)?"
        message="Матч будет аннулирован. При необходимости произойдёт пересчёт."
        confirmLabel="Отменить матч"
        danger
        onConfirm={async () => {
          if (voidId !== null) {
            await onVoid(voidId);
            setVoidId(null);
          }
        }}
        onCancel={() => setVoidId(null)}
      />
    </div>
  );
}
