"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { PublicTabs, type PublicTab } from "@/components/contest/PublicTabs";
import { RoundSelector } from "@/components/contest/RoundSelector";
import { PredictionsMatrix } from "@/components/predictions/PredictionsMatrix";
import { PredictionsVisitorStub } from "@/components/predictions/PredictionsVisitorStub";
import { OutcomeStatsFooter } from "@/components/predictions/OutcomeStatsFooter";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { useAuth } from "@/hooks/useAuth";
import { useContest } from "@/hooks/useContest";
import { usePredictionsView } from "@/hooks/usePredictionsView";
import { useRounds } from "@/hooks/useRounds";
import { formatRoundTitle } from "@/lib/admin/roundLabel";
import { isDeadlinePassedNow } from "@/lib/contest/deadline";
import {
  isRoundPubliclyVisible,
  ROUND_NOT_PUBLISHED_COPY,
} from "@/lib/contest/roundPublicVisibility";
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

function LeaderboardStub() {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-8 text-center text-gray-600">
      {ROUND_NOT_PUBLISHED_COPY}
    </div>
  );
}

function ResultsStub() {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-8 text-center text-gray-600">
      {ROUND_NOT_PUBLISHED_COPY}
    </div>
  );
}

export default function ContestPage() {
  const params = useParams();
  const contestId = Number(params.contestId);
  const { contest, setContestId } = useContest();
  const { isAuthenticated, user } = useAuth();
  const { rounds, loading: roundsLoading, error: roundsError } = useRounds(contestId);
  const [tab, setTab] = useState<PublicTab>("predictions");
  const [selectedRoundId, setSelectedRoundId] = useState<number | null>(null);

  useEffect(() => {
    if (Number.isInteger(contestId) && contestId > 0) {
      void setContestId(contestId);
    }
  }, [contestId, setContestId]);

  useEffect(() => {
    if (rounds.length > 0 && selectedRoundId == null) {
      setSelectedRoundId(pickDefaultRound(rounds, tab));
    }
  }, [rounds, selectedRoundId, tab]);

  const handleTabChange = (newTab: PublicTab) => {
    setTab(newTab);
    if (rounds.length > 0) {
      setSelectedRoundId(pickDefaultRound(rounds, newTab));
    }
  };

  const effectiveRoundId = useMemo(() => {
    if (rounds.length === 0) return null;
    return selectedRoundId ?? pickDefaultRound(rounds, tab);
  }, [rounds, selectedRoundId, tab]);

  const selectedRound = useMemo(
    () => rounds.find((r) => r.id === effectiveRoundId) ?? null,
    [rounds, effectiveRoundId],
  );

  const visitorPreDeadline =
    !isAuthenticated &&
    tab === "predictions" &&
    selectedRound != null &&
    selectedRound.status === "ACTIVE" &&
    !isDeadlinePassedNow(selectedRound.deadline);

  const shouldFetchPredictions =
    tab === "predictions" &&
    effectiveRoundId != null &&
    !visitorPreDeadline &&
    (isAuthenticated || selectedRound != null);

  const { data: predictionsData, loading: predictionsLoading } = usePredictionsView(
    contestId,
    effectiveRoundId,
    shouldFetchPredictions,
  );

  const showLbStub =
    tab === "leaderboard" && selectedRound && !isRoundPubliclyVisible(selectedRound.status);
  const showResultsStub =
    tab === "results" && selectedRound && !isRoundPubliclyVisible(selectedRound.status);

  if (!Number.isInteger(contestId) || contestId <= 0) {
    return <ErrorState message="Конкурс не найден" />;
  }

  if (roundsLoading) return <LoadingState />;
  if (rounds.length === 0) {
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
        {rounds.length > 0 && effectiveRoundId != null && (
          <RoundSelector
            rounds={rounds}
            selectedRoundId={effectiveRoundId}
            onChange={setSelectedRoundId}
          />
        )}
      </div>

      <PublicTabs active={tab} onChange={handleTabChange} />

      {tab === "leaderboard" && (showLbStub || !selectedRound) && <LeaderboardStub />}

      {tab === "results" && (showResultsStub || !selectedRound) && <ResultsStub />}

      {tab === "predictions" && visitorPreDeadline && <PredictionsVisitorStub />}

      {tab === "predictions" &&
        shouldFetchPredictions &&
        (predictionsLoading ? (
          <LoadingState />
        ) : predictionsData ? (
          <div className="bg-white border border-gray-200 rounded-lg p-4 overflow-x-auto">
            <PredictionsMatrix
              matches={predictionsData.matches}
              entries={predictionsData.entries}
              deadlinePassed={predictionsData.deadline_passed}
              viewer={user}
              roundTitle={selectedRound ? formatRoundTitle(selectedRound) : ""}
            />
            {predictionsData.deadline_passed && (
              <table className="min-w-full text-sm mt-0">
                <tbody>
                  <OutcomeStatsFooter
                    matches={predictionsData.matches}
                    entries={predictionsData.entries}
                  />
                </tbody>
              </table>
            )}
          </div>
        ) : null)}
    </div>
  );
}
