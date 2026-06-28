"use client";

import { formatRoundTitle } from "@/lib/admin/roundLabel";
import type { RoundOut } from "@/types/api";

interface RoundSelectorProps {
  rounds: RoundOut[];
  selectedRoundId: number | null;
  onChange: (roundId: number) => void;
  label?: string;
}

export function RoundSelector({
  rounds,
  selectedRoundId,
  onChange,
  label = "Выберите тур:",
}: RoundSelectorProps) {
  return (
    <div className="flex items-center gap-2" data-testid="round-selector">
      <label htmlFor="round-select" className="text-sm text-gray-600 whitespace-nowrap">
        {label}
      </label>
      <select
        id="round-select"
        value={selectedRoundId ?? ""}
        onChange={(e) => onChange(Number(e.target.value))}
        className="border border-gray-300 rounded px-3 py-1.5 text-sm bg-white"
      >
        {rounds.map((r) => (
          <option key={r.id} value={r.id}>
            {formatRoundTitle(r)}
          </option>
        ))}
      </select>
    </div>
  );
}
