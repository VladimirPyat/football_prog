"use client";

import { useEffect, useState } from "react";
import { deriveAdminUiMode } from "@/lib/admin/deriveAdminUiMode";
import { formatRoundOptionLabel, formatRoundTitle } from "@/lib/admin/roundLabel";
import { effectiveRoundStatus, isDeadlinePassedNow } from "@/lib/admin/roundEffectiveStatus";
import {
  BONUSES_PENDING_FALLBACK_MESSAGE,
  roundHasVisiblePostponements,
} from "@/lib/admin/roundScoringPending";
import { roundStatusHint } from "@/lib/admin/format";
import type { ContestOut, MatchOut, RoundOut } from "@/types/api";
import { MatchResultRow } from "@/components/admin/MatchResultRow";
import { RoundResultsPreview } from "@/components/admin/RoundResultsPreview";
import { AdminTable, AdminTh } from "@/components/ui/AdminTable";
import { Button } from "@/components/ui/Button";
import { Callout } from "@/components/ui/Callout";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { LoadingState } from "@/components/ui/LoadingState";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
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
        <Callout variant="info">
          Нет туров, готовых к вводу результатов. Дождитесь окончания дедлайна активного тура.
        </Callout>
      )}

      {activeRoundId != null && activeDeadlinePassed && eligibleRounds.length === 0 && (
        <Callout variant="warning">
          Дедлайн прогнозов прошёл. Прогнозы закрыты; ввод результатов — на этой вкладке после
          обновления списка туров.
        </Callout>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <Select
          label="Тур:"
          value={selectedRoundId ?? ""}
          onChange={(e) => onSelectRound(Number(e.target.value))}
        >
          <option value="">Выберите тур</option>
          {eligibleRounds.map((r) => (
            <option key={r.id} value={r.id}>
              {formatRoundOptionLabel(r)}
            </option>
          ))}
        </Select>
        {selectedRound && uiMode.showAppliedBadge && (
          <span className="text-sm font-medium text-green-700 bg-green-50 px-2 py-1 rounded">
            Применено
          </span>
        )}
      </div>

      {selectedRound && (
        <>
          <Callout variant="info">
            {roundStatusHint(displayRoundStatus ?? selectedRound.status)}
          </Callout>

          <p className="text-sm text-gray-600">
            {resultsStatusHint(displayRoundStatus ?? selectedRound.status)}
          </p>

          {showBonusesPendingNote && (
            <Callout variant="warning">
              {bonusesPendingMessage ?? BONUSES_PENDING_FALLBACK_MESSAGE}
            </Callout>
          )}

          {displayRoundStatus === "CLOSED" && (
            <Callout variant="info">
              Счёт можно вносить после времени начала каждого матча.
            </Callout>
          )}

          <AdminTable
            headers={
              <>
                <AdminTh>Матч</AdminTh>
                <AdminTh>Дата</AdminTh>
                <AdminTh>Статус</AdminTh>
                <AdminTh>Счёт</AdminTh>
                <AdminTh>Действия</AdminTh>
              </>
            }
          >
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
          </AdminTable>

          <div className="flex flex-wrap gap-3">
            {uiMode.canCalculate && allFinished && (
              <Button
                disabled={working}
                onClick={async () => {
                  setWorking(true);
                  try {
                    await onCalculate(selectedRound.id);
                  } finally {
                    setWorking(false);
                  }
                }}
              >
                Рассчитать
              </Button>
            )}
            {uiMode.canPublish && (
              <Button
                variant="success"
                disabled={working}
                onClick={async () => {
                  setWorking(true);
                  try {
                    await onPublish(selectedRound.id);
                  } finally {
                    setWorking(false);
                  }
                }}
              >
                Опубликовать
              </Button>
            )}
            {selectedRound.status === "CALCULATED" && (
              <Button variant="secondary" onClick={() => setPreviewOpen(true)}>
                Результаты участников
              </Button>
            )}
            {displayRoundStatus === "CLOSED" && (
              <span
                title="Сначала рассчитайте тур"
                className="px-4 py-2 text-sm border border-gray-200 rounded-lg text-gray-400 cursor-not-allowed"
              >
                Результаты участников
              </span>
            )}
            {selectedRound.status === "PUBLISHED" && (
              <Button variant="secondary" onClick={() => setPreviewOpen(true)}>
                Результаты участников
              </Button>
            )}
          </div>
        </>
      )}

      <Modal
        open={previewOpen && selectedRound != null}
        onClose={() => setPreviewOpen(false)}
        title={
          selectedRound
            ? `Результаты участников — ${formatRoundTitle(selectedRound)}`
            : undefined
        }
        size="xl"
        footer={
          <Button variant="secondary" onClick={() => setPreviewOpen(false)}>
            Закрыть
          </Button>
        }
      >
        {selectedRound && (
          <RoundResultsPreview
            contestId={contest.id}
            roundId={selectedRound.id}
            roundLabel={formatRoundTitle(selectedRound)}
            preview={selectedRound.status === "CALCULATED"}
          />
        )}
      </Modal>

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
