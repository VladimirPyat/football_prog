"use client";

import { formatRoundTitle } from "@/lib/admin/roundLabel";
import type { RoundOut } from "@/types/api";
import { Select } from "@/components/ui/Select";

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
    <div data-testid="round-selector">
      <Select
        id="round-select"
        label={label}
        value={selectedRoundId ?? ""}
        onChange={(e) => onChange(Number(e.target.value))}
      >
        {rounds.map((r) => (
          <option key={r.id} value={r.id}>
            {formatRoundTitle(r)}
          </option>
        ))}
      </Select>
    </div>
  );
}
