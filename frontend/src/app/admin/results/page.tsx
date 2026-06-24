"use client";

import { useEffect, useState } from "react";
import { AdminPageShell } from "@/components/admin/AdminPageShell";
import { ResultsEntryPanel } from "@/components/admin/ResultsEntryPanel";
import { useContest } from "@/hooks/useContest";
import { useContestAdmin } from "@/hooks/useContestAdmin";
import { useAdminRounds } from "@/hooks/useAdminRounds";
import { useRoundMatches } from "@/hooks/useRoundMatches";
import { useAdminResults } from "@/hooks/useAdminResults";
import { useToast } from "@/hooks/useToast";
import { AppError } from "@/lib/api/client";

export default function AdminResultsPage() {
  const { contest, contestId } = useContestAdmin();
  const { maxScore } = useContest();
  const { rounds, loading, calculateRound, publishRound, refetch } = useAdminRounds(contestId);
  const [selectedRoundId, setSelectedRoundId] = useState<number | null>(null);
  const {
    matches,
    loading: matchesLoading,
    refetch: refetchMatches,
  } = useRoundMatches(contestId, selectedRoundId);
  const { putResult, patchStatus } = useAdminResults(contestId);
  const { showSuccess, showError } = useToast();

  useEffect(() => {
    const eligible = rounds.filter((r) => ["CLOSED", "CALCULATED", "PUBLISHED"].includes(r.status));
    if (eligible.length && !selectedRoundId) {
      setSelectedRoundId(eligible[eligible.length - 1].id);
    }
  }, [rounds, selectedRoundId]);

  if (!contest) return null;

  return (
    <AdminPageShell title="Результаты">
      <ResultsEntryPanel
        contest={contest}
        maxScore={maxScore}
        rounds={rounds}
        selectedRoundId={selectedRoundId}
        matches={matches}
        loading={loading || matchesLoading}
        onSelectRound={setSelectedRoundId}
        onSaveResult={async (matchId, score1, score2) => {
          try {
            await putResult(matchId, score1, score2);
            await refetchMatches();
            showSuccess("Результат сохранён");
          } catch (err) {
            showError(err instanceof AppError ? err.detail : "Ошибка");
          }
        }}
        onVoid={async (matchId) => {
          try {
            const res = await patchStatus(matchId, "VOID");
            await refetchMatches();
            await refetch();
            if (res.recalculation_triggered) {
              showSuccess("Матч отменён, выполнен пересчёт");
            } else {
              showSuccess("Матч отменён");
            }
          } catch (err) {
            showError(err instanceof AppError ? err.detail : "Ошибка");
          }
        }}
        onCalculate={async (roundId) => {
          try {
            await calculateRound(roundId);
            await refetch();
            showSuccess("Тур рассчитан");
          } catch (err) {
            showError(err instanceof AppError ? err.detail : "Ошибка расчёта");
          }
        }}
        onPublish={async (roundId) => {
          try {
            await publishRound(roundId);
            await refetch();
            showSuccess("Результаты опубликованы");
          } catch (err) {
            showError(err instanceof AppError ? err.detail : "Ошибка публикации");
          }
        }}
      />
    </AdminPageShell>
  );
}
