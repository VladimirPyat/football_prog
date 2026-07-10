"use client";

import { useCallback, useEffect, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { ContestRoundToolbar } from "@/components/contest/ContestRoundToolbar";
import { PredictionForm } from "@/components/predictions/PredictionForm";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { useAuth } from "@/hooks/useAuth";
import { useContest } from "@/hooks/useContest";
import { usePersistedRoundSelection } from "@/hooks/usePersistedRoundSelection";
import { usePredictionsView } from "@/hooks/usePredictionsView";
import { useRounds } from "@/hooks/useRounds";
import { formatRoundTitle } from "@/lib/admin/roundLabel";
import { pickDefaultPredictRound } from "@/lib/contest/pickDefaultRound";
import { filterParticipantVisibleRounds } from "@/lib/contest/participantRoundFilter";

function PredictPageContent() {
  const params = useParams();
  const router = useRouter();
  const contestId = Number(params.contestId);
  const roundIdParam = Number(params.roundId);
  const { user } = useAuth();
  const { contest, status: contestStatus } = useContest();
  const { rounds, loading: roundsLoading } = useRounds(contestId);

  const visibleRounds = useMemo(
    () => filterParticipantVisibleRounds(rounds, user?.role),
    [rounds, user?.role],
  );

  const pickDefault = useCallback(
    () => pickDefaultPredictRound(visibleRounds),
    [visibleRounds],
  );

  const initialRoundId =
    Number.isInteger(roundIdParam) && roundIdParam > 0 ? roundIdParam : null;

  const { selectedRoundId, setSelectedRoundId } = usePersistedRoundSelection({
    contestId,
    scope: "predict",
    rounds: visibleRounds,
    pickDefault,
    initialRoundId,
  });

  const roundId = selectedRoundId ?? roundIdParam;

  const { data, loading, error, refetch } = usePredictionsView(contestId, roundId);

  const round = useMemo(
    () => visibleRounds.find((r) => r.id === roundId) ?? null,
    [visibleRounds, roundId],
  );

  useEffect(() => {
    if (
      selectedRoundId != null &&
      selectedRoundId !== roundIdParam &&
      Number.isInteger(contestId) &&
      contestId > 0
    ) {
      router.replace(`/contest/${contestId}/predict/${selectedRoundId}`);
    }
  }, [selectedRoundId, roundIdParam, contestId, router]);

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
            setSelectedRoundId(id);
            router.push(`/contest/${contestId}/predict/${id}`);
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
