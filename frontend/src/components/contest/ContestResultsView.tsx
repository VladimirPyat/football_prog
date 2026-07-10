"use client";

import { ResultsMatrix } from "@/components/contest/ResultsMatrix";
import { ResultsUnavailableMessage } from "@/components/contest/ResultsUnavailableMessage";
import { Callout } from "@/components/ui/Callout";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { PreviewBadge } from "@/components/ui/PreviewBadge";
import { useRoundResults } from "@/hooks/useRoundResults";
import { ROUND_NOT_PUBLISHED_COPY } from "@/lib/contest/roundPublicVisibility";

export interface ContestResultsViewProps {
  contestId: number;
  roundId: number | null;
  roundLabel: string;
  enabled?: boolean;
  preview?: boolean;
  notPublishedMessage?: string;
}

export function ContestResultsView({
  contestId,
  roundId,
  roundLabel,
  enabled = true,
  preview = false,
  notPublishedMessage = ROUND_NOT_PUBLISHED_COPY,
}: ContestResultsViewProps) {
  const shouldFetch = enabled && roundId != null;
  const { data, loading, error, notAvailable, pointsMissing } = useRoundResults(
    contestId,
    roundId,
    shouldFetch,
  );

  if (!shouldFetch) {
    return <ResultsUnavailableMessage message={notPublishedMessage} />;
  }

  if (loading) return <LoadingState message="Загрузка результатов тура…" />;
  if (notAvailable) return <ResultsUnavailableMessage message={notPublishedMessage} />;
  if (error) return <ErrorState message={error} />;
  if (!data?.rows.length) {
    return <EmptyState message="Очки не рассчитаны или участники отсутствуют." />;
  }
  if (pointsMissing) {
    return <Callout variant="warning">Очки по матчам ещё не рассчитаны.</Callout>;
  }

  return (
    <div className="space-y-3">
      {preview && <PreviewBadge />}
      <ResultsMatrix matches={data.matches} rows={data.rows} roundLabel={roundLabel} />
    </div>
  );
}
