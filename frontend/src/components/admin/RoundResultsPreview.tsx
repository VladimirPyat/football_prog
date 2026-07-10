"use client";

import { ContestResultsView } from "@/components/contest/ContestResultsView";

interface RoundResultsPreviewProps {
  contestId: number;
  roundId: number;
  roundLabel: string;
  preview?: boolean;
}

export function RoundResultsPreview({
  contestId,
  roundId,
  roundLabel,
  preview = false,
}: RoundResultsPreviewProps) {
  return (
    <ContestResultsView
      contestId={contestId}
      roundId={roundId}
      roundLabel={roundLabel}
      enabled
      preview={preview}
    />
  );
}
