"use client";

import { ContestPicker } from "@/components/contest/ContestPicker";
import { RoundSelector } from "@/components/contest/RoundSelector";
import { useAuth } from "@/hooks/useAuth";
import type { RoundOut } from "@/types/api";

interface ContestRoundToolbarProps {
  rounds: RoundOut[];
  selectedRoundId: number | null;
  onRoundChange: (roundId: number) => void;
}

export function ContestRoundToolbar({
  rounds,
  selectedRoundId,
  onRoundChange,
}: ContestRoundToolbarProps) {
  const { isAuthenticated } = useAuth();

  return (
    <div
      className="flex flex-col items-stretch sm:items-end gap-2"
      data-testid="contest-round-toolbar"
    >
      {isAuthenticated && <ContestPicker />}
      <RoundSelector rounds={rounds} selectedRoundId={selectedRoundId} onChange={onRoundChange} />
    </div>
  );
}
