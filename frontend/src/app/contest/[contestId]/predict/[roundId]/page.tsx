"use client";

import { useEffect, useMemo } from "react";
import { useParams } from "next/navigation";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { ContestRoundToolbar } from "@/components/contest/ContestRoundToolbar";
import { PredictionForm } from "@/components/predictions/PredictionForm";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { useAuth } from "@/hooks/useAuth";
import { useContest } from "@/hooks/useContest";
import { usePredictionsView } from "@/hooks/usePredictionsView";
import { useRounds } from "@/hooks/useRounds";
import { formatRoundTitle } from "@/lib/admin/roundLabel";
import { filterParticipantVisibleRounds } from "@/lib/contest/participantRoundFilter";

function PredictPageContent() {
  const params = useParams();
  const contestId = Number(params.contestId);
  const roundId = Number(params.roundId);
  const { user } = useAuth();
  const { contest, status: contestStatus } = useContest();
  const { rounds, loading: roundsLoading } = useRounds(contestId);
  const { data, loading, error, refetch } = usePredictionsView(contestId, roundId);

  const visibleRounds = useMemo(
    () => filterParticipantVisibleRounds(rounds, user?.role),
    [rounds, user?.role],
  );

  const round = useMemo(
    () => visibleRounds.find((r) => r.id === roundId) ?? null,
    [visibleRounds, roundId],
  );

  if (roundsLoading || loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (!data || !round || !user) {
    return <ErrorState message="Тур не найден или недоступен" />;
  }

  const contestName = contest?.name ?? `Конкурс #${contestId}`;

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{contestName}</h1>
          <p className="text-gray-600">{formatRoundTitle(round)}</p>
        </div>
        <ContestRoundToolbar
          rounds={visibleRounds}
          selectedRoundId={roundId}
          onRoundChange={(id) => {
            window.location.href = `/contest/${contestId}/predict/${id}`;
          }}
        />
      </div>

      <PredictionForm
        contestId={contestId}
        round={round}
        matches={data.matches}
        entries={data.entries}
        deadlinePassed={data.deadline_passed}
        userId={user.id}
        contestPaused={contestStatus === "PAUSED"}
        onSaved={() => void refetch()}
      />
    </div>
  );
}

export default function PredictPage() {
  const params = useParams();
  const contestId = Number(params.contestId);
  const { setContestId } = useContest();

  useEffect(() => {
    if (Number.isInteger(contestId) && contestId > 0) {
      void setContestId(contestId);
    }
  }, [contestId, setContestId]);

  return (
    <ProtectedRoute requireAuth requireRole="USER" requireNotTempPassword>
      <PredictPageContent />
    </ProtectedRoute>
  );
}
