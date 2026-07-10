"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { PublicTabs, type PublicTab } from "@/components/contest/PublicTabs";
import { ContestRoundToolbar } from "@/components/contest/ContestRoundToolbar";
import { ContestLeaderboardView } from "@/components/contest/ContestLeaderboardView";
import { ContestResultsView } from "@/components/contest/ContestResultsView";
import { PredictionsMatrix } from "@/components/predictions/PredictionsMatrix";
import { PredictionsVisitorStub } from "@/components/predictions/PredictionsVisitorStub";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { filterParticipantEntries } from "@/lib/predictions/filterMatrixEntries";
import { useAuth } from "@/hooks/useAuth";
import { useContest } from "@/hooks/useContest";
import { usePersistedRoundSelection } from "@/hooks/usePersistedRoundSelection";
import { usePredictionsView } from "@/hooks/usePredictionsView";
import { useRounds } from "@/hooks/useRounds";
import { formatRoundTitle } from "@/lib/admin/roundLabel";
import { isDeadlinePassedNow } from "@/lib/contest/deadline";
import { pickDefaultRound } from "@/lib/contest/pickDefaultRound";
import { filterParticipantVisibleRounds } from "@/lib/contest/participantRoundFilter";
import { shouldFetchPublicResults } from "@/lib/results/roundResultsGuard";

export default function ContestPage() {
  const params = useParams();
  const contestId = Number(params.contestId);
  const { contest, setContestId } = useContest();
  const { isAuthenticated, user } = useAuth();
  const { rounds, loading: roundsLoading, error: roundsError } = useRounds(contestId);
  const [tab, setTab] = useState<PublicTab>("predictions");

  const visibleRounds = useMemo(
    () => filterParticipantVisibleRounds(rounds, user?.role),
    [rounds, user?.role],
  );

  const pickDefault = useCallback(
    () => pickDefaultRound(visibleRounds, tab),
    [visibleRounds, tab],
  );

  const { selectedRoundId, setSelectedRoundId } = usePersistedRoundSelection({
    contestId,
    scope: "contest-public",
    rounds: visibleRounds,
    pickDefault,
  });

  useEffect(() => {
    if (Number.isInteger(contestId) && contestId > 0) {
      void setContestId(contestId);
    }
  }, [contestId, setContestId]);

  const effectiveRoundId = selectedRoundId;

  const selectedRound = useMemo(
    () => visibleRounds.find((r) => r.id === effectiveRoundId) ?? null,
    [visibleRounds, effectiveRoundId],
  );

  const isAdminViewer = user?.role === "ADMIN";
  const roundIsPublished =
    selectedRound != null && shouldFetchPublicResults(selectedRound.status);

  const showPredictionsPreDeadlineStub =
    tab === "predictions" &&
    selectedRound != null &&
    !isDeadlinePassedNow(selectedRound.deadline) &&
    !isAdminViewer;

  const shouldFetchPredictions =
    tab === "predictions" &&
    effectiveRoundId != null &&
    !showPredictionsPreDeadlineStub &&
    (isAuthenticated || selectedRound != null);

  const { data: predictionsData, loading: predictionsLoading } = usePredictionsView(
    contestId,
    effectiveRoundId,
    shouldFetchPredictions,
  );

  const participantEntries = useMemo(
    () => (predictionsData ? filterParticipantEntries(predictionsData.entries) : []),
    [predictionsData],
  );

  if (!Number.isInteger(contestId) || contestId <= 0) {
    return <ErrorState message="Конкурс не найден" />;
  }

  if (roundsLoading) return <LoadingState />;
  if (visibleRounds.length === 0) {
    return <ErrorState message={roundsError ?? "Туры не найдены"} />;
  }
  if (effectiveRoundId == null) return <LoadingState />;

  const roundLabel = selectedRound ? formatRoundTitle(selectedRound) : "";

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {contest?.name ?? `Конкурс #${contestId}`}
          </h1>
          <p className="text-gray-600 mt-1">
            Добро пожаловать! Просмотрите таблицу лидеров, прогнозы и результаты матчей.
          </p>
        </div>
        {visibleRounds.length > 0 && effectiveRoundId != null && (
          <ContestRoundToolbar
            rounds={visibleRounds}
            selectedRoundId={effectiveRoundId}
            onRoundChange={setSelectedRoundId}
          />
        )}
      </div>

      <PublicTabs active={tab} onChange={setTab} />

      {tab === "leaderboard" && selectedRound && (
        <ContestLeaderboardView
          contestId={contestId}
          roundId={effectiveRoundId}
          enabled={roundIsPublished}
        />
      )}

      {tab === "results" && selectedRound && (
        <ContestResultsView
          contestId={contestId}
          roundId={effectiveRoundId}
          roundLabel={roundLabel}
          enabled={roundIsPublished}
        />
      )}

      {tab === "predictions" && showPredictionsPreDeadlineStub && (
        <PredictionsVisitorStub showOwnPredictionHint={isAuthenticated} />
      )}

      {tab === "predictions" &&
        shouldFetchPredictions &&
        (predictionsLoading ? (
          <LoadingState />
        ) : predictionsData ? (
          <PredictionsMatrix
            matches={predictionsData.matches}
            entries={participantEntries}
            deadlinePassed={predictionsData.deadline_passed}
            viewer={user}
            roundTitle={roundLabel}
            showStats={predictionsData.deadline_passed}
          />
        ) : null)}
    </div>
  );
}
