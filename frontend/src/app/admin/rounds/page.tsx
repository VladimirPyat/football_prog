"use client";

import { useCallback, useEffect, useState } from "react";
import { AdminPageShell } from "@/components/admin/AdminPageShell";
import { RoundManagementPanel } from "@/components/admin/RoundManagementPanel";
import { useContestAdmin } from "@/hooks/useContestAdmin";
import { useAdminRounds } from "@/hooks/useAdminRounds";
import { useRoundMatches } from "@/hooks/useRoundMatches";
import { useTeams } from "@/hooks/useTeams";
import { useToast } from "@/hooks/useToast";
import { isDeadlinePassedNow } from "@/lib/admin/roundEffectiveStatus";
import { AppError } from "@/lib/api/client";

export default function AdminRoundsPage() {
  const { contest, contestId, refetch: refetchContest } = useContestAdmin();
  const { rounds, loading, refetch: refetchRounds, createRound, activateRound, updateRound, createFreeTour } =
    useAdminRounds(contestId);
  const { teams } = useTeams(contestId);
  const [selectedRoundId, setSelectedRoundId] = useState<number | null>(null);
  const handleDeadlinePassed = useCallback(() => {
    void refetchRounds();
  }, [refetchRounds]);
  const {
    matches,
    deadlinePassed,
    loading: matchesLoading,
    refetch: refetchMatches,
  } = useRoundMatches(contestId, selectedRoundId, {
    onDeadlinePassed: handleDeadlinePassed,
  });
  const { showSuccess, showError } = useToast();

  const selectedRound = rounds.find((r) => r.id === selectedRoundId) ?? null;
  const effectiveDeadlinePassed =
    deadlinePassed ||
    (selectedRound != null && isDeadlinePassedNow(selectedRound.deadline));

  useEffect(() => {
    if (effectiveDeadlinePassed && selectedRound?.status === "ACTIVE") {
      void refetchRounds();
    }
  }, [effectiveDeadlinePassed, selectedRound?.status, selectedRound?.id, refetchRounds]);

  useEffect(() => {
    if (rounds.length && !selectedRoundId) {
      setSelectedRoundId(rounds[rounds.length - 1].id);
    }
  }, [rounds, selectedRoundId]);

  if (!contest) return null;

  return (
    <AdminPageShell title="Туры">
      <RoundManagementPanel
        contest={contest}
        rounds={rounds}
        teams={teams}
        selectedRoundId={selectedRoundId}
        matches={matches}
        deadlinePassed={effectiveDeadlinePassed}
        loading={loading || matchesLoading}
        onSelectRound={setSelectedRoundId}
        onCreateRound={async (data) => {
          try {
            const res = await createRound(data);
            setSelectedRoundId(res.round_id);
            showSuccess("Черновик тура создан");
          } catch (err) {
            showError(err instanceof AppError ? err.detail : "Ошибка");
          }
        }}
        onActivate={async (roundId) => {
          try {
            await activateRound(roundId);
            await refetchContest();
            showSuccess("Тур активирован");
          } catch (err) {
            showError(err instanceof AppError ? err.detail : "Ошибка активации");
          }
        }}
        onUpdateRound={async (roundId, body) => {
          try {
            await updateRound(roundId, body);
            showSuccess("Изменения сохранены");
          } catch (err) {
            showError(err instanceof AppError ? err.detail : "Ошибка сохранения");
          }
        }}
        onCreateFreeTour={async (data) => {
          try {
            await createFreeTour(data);
            showSuccess("Свободный тур создан");
          } catch (err) {
            showError(err instanceof AppError ? err.detail : "Ошибка");
          }
        }}
        onRefetchMatches={refetchMatches}
        refetchContest={refetchContest}
      />
    </AdminPageShell>
  );
}
