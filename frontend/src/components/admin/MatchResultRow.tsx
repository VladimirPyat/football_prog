"use client";

import { formatDateTimeRu } from "@/lib/admin/format";
import { matchResultSchema } from "@/lib/validation/admin";
import type { MatchOut } from "@/types/api";
import { useState } from "react";

interface MatchResultRowProps {
  match: MatchOut;
  maxScore: number;
  scoresReadonly: boolean;
  canVoid: boolean;
  onSave: (matchId: number, score1: number, score2: number) => Promise<void>;
  onVoid: (matchId: number) => void;
}

export function MatchResultRow({
  match,
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

  const finished = match.status === "FINISHED" || match.status === "VOID";

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
      <td className="px-3 py-2 text-sm">{match.status}</td>
      <td className="px-3 py-2">
        <div className="flex items-center gap-2">
          <input
            type="number"
            min={0}
            max={maxScore}
            value={score1}
            onChange={(e) => setScore1(e.target.value === "" ? "" : Number(e.target.value))}
            disabled={scoresReadonly || finished}
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
            disabled={scoresReadonly || finished}
            className="w-14 border border-gray-300 rounded px-2 py-1 text-sm disabled:bg-gray-100"
            aria-label="Счёт 2"
          />
        </div>
        {error && <p className="text-xs text-red-600 mt-1">{error}</p>}
      </td>
      <td className="px-3 py-2 space-x-2">
        {!scoresReadonly && !finished && (
          <button
            type="button"
            onClick={handleFinish}
            disabled={saving}
            className="text-sm text-green-600 hover:underline disabled:opacity-50"
          >
            Завершён
          </button>
        )}
        {canVoid && match.status !== "VOID" && (
          <button
            type="button"
            onClick={() => onVoid(match.id)}
            className="text-sm text-red-600 hover:underline"
          >
            Отменить
          </button>
        )}
      </td>
    </tr>
  );
}
