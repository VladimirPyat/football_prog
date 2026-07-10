"use client";

import { useCallback, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { AdminPageShell } from "@/components/admin/AdminPageShell";
import { ResultsEntryPanel } from "@/components/admin/ResultsEntryPanel";
import { useContest } from "@/hooks/useContest";
import { useContestAdmin } from "@/hooks/useContestAdmin";
import { useAdminRounds } from "@/hooks/useAdminRounds";
import { useRoundMatches } from "@/hooks/useRoundMatches";
import { useAdminResults } from "@/hooks/useAdminResults";
import { usePersistedRoundSelection } from "@/hooks/usePersistedRoundSelection";
import { useToast } from "@/hooks/useToast";
import { isDeadlinePassedNow } from "@/lib/admin/roundEffectiveStatus";
import { AppError } from "@/lib/api/client";

export default function AdminResultsPage() {
  const searchParams = useSearchParams();
  const { contest, contestId } = useContestAdmin();
  const { maxScore } = useContest();
  const { rounds, loading, calculateRound, publishRound, refetch } = useAdminRounds(contestId);
  const activeRound = rounds.find((r) => r.status === "ACTIVE") ?? null;

  const roundFromUrl = Number(searchParams.get("round"));
  const initialRoundId =
    Number.isInteger(roundFromUrl) && roundFromUrl > 0 ? roundFromUrl : null;

  const handleActiveDeadlinePassed = useCallback(() => {
    void refetch();
  }, [refetch]);

  const { deadlinePassed: activeDeadlinePassed } = useRoundMatches(
    contestId,
    activeRound?.id ?? null,
    { onDeadlinePassed: handleActiveDeadlinePassed },
  );

  const effectiveActiveDeadlinePassed =
    activeDeadlinePassed || (activeRound != null && isDeadlinePassedNow(activeRound.deadline));

  const eligibleRounds = rounds.filter(
    (r) =>
      ["CLOSED", "CALCULATED", "PUBLISHED"].includes(r.status) ||
      (r.id === activeRound?.id && effectiveActiveDeadlinePassed),
  );

  const pickDefault = useCallback(() => {
    if (!eligibleRounds.length) return null;
    return eligibleRounds[eligibleRounds.length - 1].id;
  }, [eligibleRounds]);

  const { selectedRoundId, setSelectedRoundId } = usePersistedRoundSelection({
    contestId,
    scope: "admin-results",
    rounds: eligibleRounds,
    pickDefault,
    initialRoundId,
  });

  const {
    matches: resultMatches,
    loading: resultMatchesLoading,
    refetch: refetchResultMatches,
  } = useRoundMatches(contestId, selectedRoundId);
  const { putResult, patchStatus } = useAdminResults(contestId);
  const { showSuccess, showError } = useToast();

  useEffect(() => {
    if (effectiveActiveDeadlinePassed && activeRound?.status === "ACTIVE") {
      void refetch();
    }
  }, [effectiveActiveDeadlinePassed, activeRound?.status, activeRound?.id, refetch]);

  if (!contest) return null;

  return (
    <AdminPageShell title="Результаты">
      <ResultsEntryPanel
        contest={contest}
        maxScore={maxScore}
        rounds={rounds}
        selectedRoundId={selectedRoundId}
        matches={resultMatches}
        loading={loading || resultMatchesLoading}
        activeRoundId={activeRound?.id ?? null}
        activeDeadlinePassed={effectiveActiveDeadlinePassed}
        onSelectRound={setSelectedRoundId}
        onSaveResult={async (matchId, score1, score2) => {
          try {
            await putResult(matchId, score1, score2);
            await refetchResultMatches();
            showSuccess("Результат сохранён");
          } catch (err) {
            showError(err instanceof AppError ? err.detail : "Ошибка");
          }
        }}
        onVoid={async (matchId) => {
          try {
            const res = await patchStatus(matchId, "VOID");
            await refetchResultMatches();
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
