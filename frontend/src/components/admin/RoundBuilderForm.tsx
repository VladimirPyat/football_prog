"use client";

import { useState } from "react";
import { fromDatetimeLocal } from "@/lib/admin/format";
import { roundBuilderSchema } from "@/lib/validation/admin";
import type { TeamOut } from "@/types/api";

interface MatchDraft {
  team1_id: number;
  team2_id: number;
  date_time: string;
}

interface RoundBuilderFormProps {
  teams: TeamOut[];
  matchesPerRound: number;
  rules: Record<string, unknown>;
  nextRoundNumber: number;
  disabled?: boolean;
  onSubmit: (data: { number: number; deadline: string; matches: MatchDraft[] }) => Promise<void>;
}

function emptyMatch(): MatchDraft {
  return { team1_id: 0, team2_id: 0, date_time: "" };
}

export function RoundBuilderForm({
  teams,
  matchesPerRound,
  rules,
  nextRoundNumber,
  disabled = false,
  onSubmit,
}: RoundBuilderFormProps) {
  const [number, setNumber] = useState(nextRoundNumber);
  const [deadline, setDeadline] = useState("");
  const [matches, setMatches] = useState<MatchDraft[]>([emptyMatch()]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const schema = roundBuilderSchema(matchesPerRound, rules);

  const updateMatch = (index: number, patch: Partial<MatchDraft>) => {
    setMatches((prev) => prev.map((m, i) => (i === index ? { ...m, ...patch } : m)));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (disabled) return;
    setErrors({});
    const payload = {
      number,
      deadline: deadline ? fromDatetimeLocal(deadline) : "",
      matches: matches.map((m) => ({
        ...m,
        date_time: m.date_time ? fromDatetimeLocal(m.date_time) : "",
      })),
    };
    const parsed = schema.safeParse(payload);
    if (!parsed.success) {
      const next: Record<string, string> = {};
      parsed.error.issues.forEach((i) => {
        next[i.path.join(".") || "form"] = i.message;
      });
      setErrors(next);
      return;
    }
    setSubmitting(true);
    try {
      await onSubmit(parsed.data);
      setMatches([emptyMatch()]);
      setDeadline("");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="border border-gray-200 rounded-lg p-4 space-y-4">
      <h3 className="text-sm font-semibold text-gray-900">Создать тур (черновик)</h3>
      <div className="grid grid-cols-2 gap-4 max-w-md">
        <div>
          <label className="block text-sm text-gray-700 mb-1">Номер тура</label>
          <input
            type="number"
            value={number}
            onChange={(e) => setNumber(Number(e.target.value))}
            disabled={disabled}
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm text-gray-700 mb-1">Дедлайн прогнозов</label>
          <input
            type="datetime-local"
            value={deadline}
            onChange={(e) => setDeadline(e.target.value)}
            disabled={disabled}
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
          />
          {errors.deadline && <p className="text-sm text-red-600">{errors.deadline}</p>}
        </div>
      </div>

      <div className="space-y-3">
        {matches.map((m, i) => (
          <div key={i} className="grid grid-cols-1 sm:grid-cols-4 gap-2 items-end">
            <select
              value={m.team1_id || ""}
              onChange={(e) => updateMatch(i, { team1_id: Number(e.target.value) })}
              disabled={disabled}
              className="border border-gray-300 rounded px-2 py-1 text-sm"
            >
              <option value="">Команда 1</option>
              {teams.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
            <select
              value={m.team2_id || ""}
              onChange={(e) => updateMatch(i, { team2_id: Number(e.target.value) })}
              disabled={disabled}
              className="border border-gray-300 rounded px-2 py-1 text-sm"
            >
              <option value="">Команда 2</option>
              {teams.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
            <input
              type="datetime-local"
              value={m.date_time}
              onChange={(e) => updateMatch(i, { date_time: e.target.value })}
              disabled={disabled}
              className="border border-gray-300 rounded px-2 py-1 text-sm"
            />
            {matches.length > 1 && (
              <button
                type="button"
                onClick={() => setMatches((prev) => prev.filter((_, j) => j !== i))}
                className="text-sm text-red-600"
              >
                Удалить
              </button>
            )}
          </div>
        ))}
        {errors.matches && <p className="text-sm text-red-600">{errors.matches}</p>}
        {matches.length < matchesPerRound && (
          <button
            type="button"
            onClick={() => setMatches((prev) => [...prev, emptyMatch()])}
            disabled={disabled}
            className="text-sm text-blue-600 hover:underline"
          >
            + Добавить матч
          </button>
        )}
      </div>

      <button
        type="submit"
        disabled={disabled || submitting}
        className="px-4 py-2 text-sm text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50"
      >
        Создать черновик тура
      </button>
    </form>
  );
}
