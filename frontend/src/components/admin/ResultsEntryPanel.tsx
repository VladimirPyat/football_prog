"use client";

import Link from "next/link";
import { deriveAdminUiMode } from "@/lib/admin/deriveAdminUiMode";
import { roundStatusLabel } from "@/lib/admin/format";
import type { ContestOut, MatchOut, RoundOut } from "@/types/api";
import { MatchResultRow } from "@/components/admin/MatchResultRow";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { LoadingState } from "@/components/ui/LoadingState";
import { useState } from "react";

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
  onCloseRound?: (roundId: number) => Promise<void>;
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
  onCloseRound,
}: ResultsEntryPanelProps) {
  const selectedRound = rounds.find((r) => r.id === selectedRoundId) ?? null;
  const uiMode = deriveAdminUiMode({ contest, round: selectedRound, matches });
  const [voidId, setVoidId] = useState<number | null>(null);
  const [working, setWorking] = useState(false);
  const [closing, setClosing] = useState(false);

  const eligibleRounds = rounds.filter((r) =>
    ["CLOSED", "CALCULATED", "PUBLISHED"].includes(r.status),
  );

  const allFinished = matches.every(
    (m) => m.status === "FINISHED" || m.status === "VOID" || m.status === "CANCELED",
  );

  if (loading && !rounds.length) return <LoadingState message="Загрузка…" />;

  return (
    <div className="space-y-6">
      {eligibleRounds.length === 0 && (
        <p className="text-sm text-gray-600 bg-gray-50 border border-gray-200 rounded px-4 py-3">
          Нет туров, готовых к вводу результатов. Закройте активный тур на странице «Туры».
        </p>
      )}

      {activeRoundId != null && activeDeadlinePassed && onCloseRound && (
        <div className="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded px-4 py-3 flex flex-wrap items-center justify-between gap-3">
          <span>Дедлайн прошёл. Закройте тур, чтобы ввести результаты.</span>
          <button
            type="button"
            disabled={closing}
            onClick={async () => {
              setClosing(true);
              try {
                await onCloseRound(activeRoundId);
              } finally {
                setClosing(false);
              }
            }}
            className="px-3 py-1.5 text-sm text-white bg-amber-600 rounded hover:bg-amber-700 disabled:opacity-50"
          >
            {closing ? "Закрытие…" : "Закрыть тур"}
          </button>
        </div>
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
              Тур {r.number} — {roundStatusLabel(r.status)}
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
          <p className="text-sm text-gray-600">
            Введите счёт для каждого матча и нажмите «Применить». Когда все матчи завершены —
            «Рассчитать», затем «Опубликовать».
          </p>

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
            {selectedRound.status === "PUBLISHED" ? (
              <Link
                href={`/contest/${contest.id}`}
                className="px-4 py-2 text-sm border border-gray-300 rounded hover:bg-gray-50"
              >
                Проверить публичные результаты
              </Link>
            ) : (
              <span
                title="Сначала опубликуйте тур"
                className="px-4 py-2 text-sm border border-gray-200 rounded text-gray-400 cursor-not-allowed"
              >
                Проверить публичные результаты
              </span>
            )}
          </div>
        </>
      )}

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
