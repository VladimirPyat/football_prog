"use client";

import { ContestLeaderboardView } from "@/components/contest/ContestLeaderboardView";

interface RoundLeaderboardPreviewProps {
  contestId: number;
  roundId: number;
}

/**
 * Admin-only preview of the round leaderboard for CALCULATED rounds (§9.5).
 * Reuses public LeaderboardTable via ContestLeaderboardView.
 */
export function RoundLeaderboardPreview({ contestId, roundId }: RoundLeaderboardPreviewProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <h4 className="text-sm font-semibold text-gray-900">Таблица тура</h4>
      </div>
      <ContestLeaderboardView
        contestId={contestId}
        roundId={roundId}
        enabled
        preview
        compact
        maxRows={10}
      />
    </div>
  );
}
