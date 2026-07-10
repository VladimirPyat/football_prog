"use client";

import { formatDateTimeRu, matchPhaseLabel, matchStatusLabel } from "@/lib/admin/format";
import { canEnterMatchResult } from "@/lib/admin/matchResultsGating";
import { matchResultSchema } from "@/lib/validation/admin";
import type { MatchOut } from "@/types/api";
import { useState } from "react";
import { Button } from "@/components/ui/Button";

interface MatchResultRowProps {
  match: MatchOut;
  /** Effective round phase (CLOSED when ACTIVE + deadline passed). */
  roundStatus: string;
  maxScore: number;
  scoresReadonly: boolean;
  canVoid: boolean;
  onSave: (matchId: number, score1: number, score2: number) => Promise<void>;
  onVoid: (matchId: number) => void;
}

export function MatchResultRow({
  match,
  roundStatus,
  maxScore,
  scoresReadonly,
  canVoid,
  onSave,
  onVoid,
}: MatchResultRowProps) {
  const [score1, setScore1] = useState(match.score1 ?? "");
  const [score2, setScore2] = useState(match.score2 ?? "");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const canEnter = canEnterMatchResult(match, { status: roundStatus });
  const inputsDisabled = scoresReadonly || !canEnter;
  const isTerminal = match.status === "VOID" || match.status === "CANCELED";
  const scoresComplete = score1 !== "" && score2 !== "";
  const showApply = canEnter && !scoresReadonly && !isTerminal;

  const statusLabel =
    roundStatus === "CLOSED"
      ? matchPhaseLabel(match.status, match.date_time, roundStatus)
      : matchStatusLabel(match.status);

  const handleFinish = async () => {
    setError(null);
    const parsed = matchResultSchema(maxScore).safeParse({ score1, score2 });
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? "Ошибка");
      return;
    }
    setSaving(true);
    try {
      await onSave(match.id, parsed.data.score1, parsed.data.score2);
    } finally {
      setSaving(false);
    }
  };

  return (
    <tr className="border-t border-gray-200">
      <td className="px-3 py-2 text-sm">
        {match.team1} — {match.team2}
      </td>
      <td className="px-3 py-2 text-sm">{formatDateTimeRu(match.date_time)}</td>
      <td className="px-3 py-2 text-sm">{statusLabel}</td>
      <td className="px-3 py-2">
        <div className="flex items-center gap-2">
          <input
            type="number"
            min={0}
            max={maxScore}
            value={score1}
            onChange={(e) => setScore1(e.target.value === "" ? "" : Number(e.target.value))}
            disabled={inputsDisabled}
            className="w-14 border border-gray-300 rounded px-2 py-1 text-sm disabled:bg-gray-100"
            aria-label="Счёт 1"
          />
          <span>:</span>
          <input
            type="number"
            min={0}
            max={maxScore}
            value={score2}
            onChange={(e) => setScore2(e.target.value === "" ? "" : Number(e.target.value))}
            disabled={inputsDisabled}
            className="w-14 border border-gray-300 rounded px-2 py-1 text-sm disabled:bg-gray-100"
            aria-label="Счёт 2"
          />
        </div>
        {error && <p className="text-xs text-red-600 mt-1">{error}</p>}
        {!canEnter && !isTerminal && roundStatus === "CLOSED" && (
          <p className="text-xs text-gray-500 mt-1">Матч ещё не начался</p>
        )}
      </td>
      <td className="px-3 py-2 space-x-2">
        {showApply && (
          <Button
            type="button"
            variant="link"
            className="!text-green-600"
            onClick={handleFinish}
            disabled={saving || !scoresComplete}
            title={!scoresComplete ? "Укажите счёт для обеих команд" : undefined}
          >
            Применить
          </Button>
        )}
        {canVoid && match.status !== "VOID" && (
          <Button type="button" variant="ghostLink" onClick={() => onVoid(match.id)}>
            Отменить
          </Button>
        )}
      </td>
    </tr>
  );
}
