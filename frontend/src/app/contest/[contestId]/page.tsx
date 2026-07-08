"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { PublicTabs, type PublicTab } from "@/components/contest/PublicTabs";
import { ContestRoundToolbar } from "@/components/contest/ContestRoundToolbar";
import { LeaderboardTable } from "@/components/contest/LeaderboardTable";
import { ResultsMatrix } from "@/components/contest/ResultsMatrix";
import { ResultsUnavailableMessage } from "@/components/contest/ResultsUnavailableMessage";
import { PredictionsMatrix } from "@/components/predictions/PredictionsMatrix";
import { PredictionsVisitorStub } from "@/components/predictions/PredictionsVisitorStub";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { filterParticipantEntries } from "@/lib/predictions/filterMatrixEntries";
import { useAuth } from "@/hooks/useAuth";
import { useContest } from "@/hooks/useContest";
import { useLeaderboard } from "@/hooks/useLeaderboard";
import { usePredictionsView } from "@/hooks/usePredictionsView";
import { useRoundResults } from "@/hooks/useRoundResults";
import { useRounds } from "@/hooks/useRounds";
import { BONUSES_PENDING_FALLBACK_MESSAGE } from "@/lib/admin/roundScoringPending";
import { formatRoundTitle } from "@/lib/admin/roundLabel";
import { isDeadlinePassedNow } from "@/lib/contest/deadline";
import { filterParticipantVisibleRounds } from "@/lib/contest/participantRoundFilter";
import {
  isRoundPubliclyVisible,
  ROUND_NOT_PUBLISHED_COPY,
} from "@/lib/contest/roundPublicVisibility";
import { mapLeaderboardRows, warnIfMissingCountColumns } from "@/lib/leaderboard/mapLeaderboardRow";
import { shouldFetchPublicResults } from "@/lib/results/roundResultsGuard";
import type { RoundOut } from "@/types/api";

function pickDefaultRound(rounds: RoundOut[], tab: PublicTab): number | null {
  if (rounds.length === 0) return null;

  if (tab === "predictions") {
    const active = rounds.find((r) => r.status === "ACTIVE");
    if (active) return active.id;
    const past = [...rounds].reverse().find((r) => r.status !== "DRAFT");
    return past?.id ?? rounds[rounds.length - 1].id;
  }

  const published = [...rounds].reverse().find((r) => isRoundPubliclyVisible(r.status));
  return published?.id ?? rounds[rounds.length - 1].id;
}

export default function ContestPage() {
  const params = useParams();
  const contestId = Number(params.contestId);
  const { contest, setContestId } = useContest();
  const { isAuthenticated, user } = useAuth();
  const { rounds, loading: roundsLoading, error: roundsError } = useRounds(contestId);
  const [tab, setTab] = useState<PublicTab>("predictions");
  const [selectedRoundId, setSelectedRoundId] = useState<number | null>(null);

  const visibleRounds = useMemo(
    () => filterParticipantVisibleRounds(rounds, user?.role),
    [rounds, user?.role],
  );

  useEffect(() => {
    if (Number.isInteger(contestId) && contestId > 0) {
      void setContestId(contestId);
    }
  }, [contestId, setContestId]);

  useEffect(() => {
    if (visibleRounds.length === 0) return;
    if (selectedRoundId == null) {
      setSelectedRoundId(pickDefaultRound(visibleRounds, tab));
      return;
    }
    const stillVisible = visibleRounds.some((r) => r.id === selectedRoundId);
    if (!stillVisible) {
      setSelectedRoundId(pickDefaultRound(visibleRounds, tab));
    }
  }, [visibleRounds, selectedRoundId, tab]);

  const handleTabChange = (newTab: PublicTab) => {
    setTab(newTab);
  };

  const effectiveRoundId = useMemo(() => {
    if (visibleRounds.length === 0) return null;
    return selectedRoundId ?? pickDefaultRound(visibleRounds, tab);
  }, [visibleRounds, selectedRoundId, tab]);

  const selectedRound = useMemo(
    () => visibleRounds.find((r) => r.id === effectiveRoundId) ?? null,
    [visibleRounds, effectiveRoundId],
  );

  const isAdminViewer = user?.role === "ADMIN";

  const roundIsPublished = selectedRound != null && shouldFetchPublicResults(selectedRound.status);

  const shouldFetchLeaderboard =
    tab === "leaderboard" && effectiveRoundId != null && roundIsPublished;

  const shouldFetchResults = tab === "results" && effectiveRoundId != null && roundIsPublished;

  const {
    data: leaderboardData,
    loading: leaderboardLoading,
    error: leaderboardError,
    notAvailable: leaderboardNotAvailable,
  } = useLeaderboard(contestId, effectiveRoundId, shouldFetchLeaderboard);

  const {
    data: resultsData,
    loading: resultsLoading,
    error: resultsError,
    notAvailable: resultsNotAvailable,
    pointsMissing: resultsPointsMissing,
  } = useRoundResults(contestId, effectiveRoundId, shouldFetchResults);

  const leaderboardRows = useMemo(() => {
    if (!leaderboardData) return [];
    return mapLeaderboardRows(leaderboardData.leaderboard);
  }, [leaderboardData]);

  const showLeaderboardCountColumns = useMemo(() => {
    if (!leaderboardData) return true;
    return warnIfMissingCountColumns(leaderboardData.leaderboard);
  }, [leaderboardData]);

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

      <PublicTabs active={tab} onChange={handleTabChange} />

      {tab === "leaderboard" && selectedRound && (
        <>
          {!roundIsPublished || leaderboardNotAvailable ? (
            <ResultsUnavailableMessage message={ROUND_NOT_PUBLISHED_COPY} />
          ) : leaderboardLoading ? (
            <LoadingState />
          ) : leaderboardError ? (
            <ErrorState message={leaderboardError} />
          ) : (
            <div className="space-y-3">
              {leaderboardData?.bonuses_pending && (
                <p className="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded px-3 py-2">
                  {leaderboardData.bonuses_pending_message ?? BONUSES_PENDING_FALLBACK_MESSAGE}
                </p>
              )}
              <LeaderboardTable
                rows={leaderboardRows}
                showCountColumns={showLeaderboardCountColumns}
              />
            </div>
          )}
        </>
      )}

      {tab === "results" && selectedRound && (
        <>
          {!roundIsPublished || resultsNotAvailable ? (
            <ResultsUnavailableMessage message={ROUND_NOT_PUBLISHED_COPY} />
          ) : resultsLoading ? (
            <LoadingState />
          ) : resultsError ? (
            <ErrorState message={resultsError} />
          ) : resultsPointsMissing ? (
            <ErrorState message="Не удалось загрузить очки по матчам" />
          ) : resultsData ? (
            <ResultsMatrix
              matches={resultsData.matches}
              rows={resultsData.rows}
              roundLabel={formatRoundTitle(selectedRound)}
            />
          ) : null}
        </>
      )}

      {tab === "predictions" && showPredictionsPreDeadlineStub && (
        <PredictionsVisitorStub showOwnPredictionHint={isAuthenticated} />
      )}

      {tab === "predictions" &&
        shouldFetchPredictions &&
        (predictionsLoading ? (
          <LoadingState />
        ) : predictionsData ? (
          <div className="bg-white border border-gray-200 rounded-lg p-4 overflow-x-auto">
            <PredictionsMatrix
              matches={predictionsData.matches}
              entries={participantEntries}
              deadlinePassed={predictionsData.deadline_passed}
              viewer={user}
              roundTitle={selectedRound ? formatRoundTitle(selectedRound) : ""}
              showStats={predictionsData.deadline_passed}
            />
          </div>
        ) : null)}
    </div>
  );
}
