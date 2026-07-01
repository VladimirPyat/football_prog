"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { PublicTabs, type PublicTab } from "@/components/contest/PublicTabs";
import { ContestRoundToolbar } from "@/components/contest/ContestRoundToolbar";
import { LeaderboardTable } from "@/components/contest/LeaderboardTable";
import { ResultsMatrix } from "@/components/contest/ResultsMatrix";
import { PredictionsMatrix } from "@/components/predictions/PredictionsMatrix";
import { PredictionsVisitorStub } from "@/components/predictions/PredictionsVisitorStub";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { filterParticipantEntries } from "@/lib/predictions/filterMatrixEntries";
import { useAuth } from "@/hooks/useAuth";
import { useContest } from "@/hooks/useContest";
import { usePredictionsView } from "@/hooks/usePredictionsView";
import { useRounds } from "@/hooks/useRounds";
import { formatRoundTitle } from "@/lib/admin/roundLabel";
import { isDeadlinePassedNow } from "@/lib/contest/deadline";
import { filterParticipantVisibleRounds } from "@/lib/contest/participantRoundFilter";
import { isRoundPubliclyVisible } from "@/lib/contest/roundPublicVisibility";
import {
  MOCK_LEADERBOARD_ROWS,
  MOCK_RESULTS_MATCHES,
  MOCK_RESULTS_ROWS,
} from "@/lib/mocks/contestDisplayMock";
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
    if (visibleRounds.length > 0 && selectedRoundId == null) {
      setSelectedRoundId(pickDefaultRound(visibleRounds, tab));
    }
  }, [visibleRounds, selectedRoundId, tab]);

  const handleTabChange = (newTab: PublicTab) => {
    setTab(newTab);
    if (visibleRounds.length > 0) {
      setSelectedRoundId(pickDefaultRound(visibleRounds, newTab));
    }
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
        <LeaderboardTable rows={MOCK_LEADERBOARD_ROWS} />
      )}

      {tab === "results" && selectedRound && (
        <ResultsMatrix
          matches={MOCK_RESULTS_MATCHES}
          rows={MOCK_RESULTS_ROWS}
          roundLabel={formatRoundTitle(selectedRound)}
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
