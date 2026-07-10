"use client";

import { useMemo } from "react";
import { LeaderboardTable } from "@/components/contest/LeaderboardTable";
import { ResultsUnavailableMessage } from "@/components/contest/ResultsUnavailableMessage";
import { Callout } from "@/components/ui/Callout";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { PreviewBadge } from "@/components/ui/PreviewBadge";
import { useLeaderboard } from "@/hooks/useLeaderboard";
import { BONUSES_PENDING_FALLBACK_MESSAGE } from "@/lib/admin/roundScoringPending";
import { mapLeaderboardRows, warnIfMissingCountColumns } from "@/lib/leaderboard/mapLeaderboardRow";
import { ROUND_NOT_PUBLISHED_COPY } from "@/lib/contest/roundPublicVisibility";

export interface ContestLeaderboardViewProps {
  contestId: number;
  roundId: number | null;
  enabled?: boolean;
  preview?: boolean;
  compact?: boolean;
  maxRows?: number;
  notPublishedMessage?: string;
}

export function ContestLeaderboardView({
  contestId,
  roundId,
  enabled = true,
  preview = false,
  compact = false,
  maxRows,
  notPublishedMessage = ROUND_NOT_PUBLISHED_COPY,
}: ContestLeaderboardViewProps) {
  const shouldFetch = enabled && roundId != null;
  const { data, loading, error, notAvailable } = useLeaderboard(
    contestId,
    roundId,
    shouldFetch,
  );

  const rows = useMemo(() => {
    if (!data) return [];
    const mapped = mapLeaderboardRows(data.leaderboard);
    return maxRows != null ? mapped.slice(0, maxRows) : mapped;
  }, [data, maxRows]);

  const showCountColumns = useMemo(() => {
    if (!data) return !compact;
    return !compact && warnIfMissingCountColumns(data.leaderboard);
  }, [data, compact]);

  if (!shouldFetch) {
    return <ResultsUnavailableMessage message={notPublishedMessage} />;
  }

  if (loading) return <LoadingState message="Загрузка таблицы…" />;
  if (notAvailable) return <ResultsUnavailableMessage message={notPublishedMessage} />;
  if (error) return <ErrorState message={error} />;
  if (!rows.length) {
    return <EmptyState message="Очки не рассчитаны или участники отсутствуют." />;
  }

  return (
    <div className="space-y-3">
      {preview && <PreviewBadge />}
      {data?.bonuses_pending && (
        <Callout variant="warning">
          {data.bonuses_pending_message ?? BONUSES_PENDING_FALLBACK_MESSAGE}
        </Callout>
      )}
      <LeaderboardTable rows={rows} showCountColumns={showCountColumns} />
    </div>
  );
}
