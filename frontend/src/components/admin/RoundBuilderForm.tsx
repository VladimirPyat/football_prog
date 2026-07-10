"use client";

import { useState } from "react";
import { fromDatetimeLocal, toDatetimeLocal } from "@/lib/admin/format";
import { nextMatchDateTime } from "@/lib/admin/roundBuilderDefaults";
import { roundBuilderSchema } from "@/lib/validation/admin";
import { Button } from "@/components/ui/Button";
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
  /** Pre-fill form for DRAFT editing (F10). */
  initialValues?: {
    number?: number;
    deadline?: string;
    matches?: MatchDraft[];
  };
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
  initialValues,
  onSubmit,
}: RoundBuilderFormProps) {
  const [number, setNumber] = useState(initialValues?.number ?? nextRoundNumber);
  const [deadline, setDeadline] = useState(
    initialValues?.deadline ? toDatetimeLocal(initialValues.deadline) : "",
  );
  const [matches, setMatches] = useState<MatchDraft[]>(
    initialValues?.matches?.length ? initialValues.matches : [emptyMatch()],
  );
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
      if (!initialValues) {
        setMatches([emptyMatch()]);
        setDeadline("");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const addMatch = () => {
    setMatches((prev) => [
      ...prev,
      { ...emptyMatch(), date_time: nextMatchDateTime(prev, deadline) },
    ]);
  };

  const isEditing = !!initialValues;

  return (
    <form onSubmit={handleSubmit} className="border border-gray-200 rounded-lg p-4 space-y-4">
      <h3 className="text-sm font-semibold text-gray-900">
        {isEditing ? "Редактировать черновик тура" : "Создать тур (черновик)"}
      </h3>
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
        {Object.keys(errors).length > 0 && (
          <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
            {errors.form ??
              errors.deadline ??
              Object.values(errors).find((msg) => msg.includes("дату и время")) ??
              "Исправьте ошибки в форме перед сохранением"}
          </p>
        )}
        {matches.map((m, i) => {
          const dateError = errors[`matches.${i}.date_time`];
          const team2Error = errors[`matches.${i}.team2_id`];
          return (
            <div key={i} className="space-y-1">
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-2 items-end">
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
                <div>
                  <input
                    type="datetime-local"
                    value={m.date_time ? toDatetimeLocal(m.date_time) : m.date_time}
                    onChange={(e) =>
                      updateMatch(i, {
                        date_time: e.target.value ? fromDatetimeLocal(e.target.value) : "",
                      })
                    }
                    disabled={disabled}
                    aria-invalid={!!dateError}
                    className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
                  />
                </div>
                {matches.length > 1 && (
                  <Button
                    type="button"
                    variant="ghostLink"
                    onClick={() => setMatches((prev) => prev.filter((_, j) => j !== i))}
                  >
                    Удалить
                  </Button>
                )}
              </div>
              {(dateError || team2Error) && (
                <p className="text-sm text-red-600">{dateError ?? team2Error}</p>
              )}
            </div>
          );
        })}
        {errors.matches && !Object.keys(errors).some((k) => k.startsWith("matches.")) && (
          <p className="text-sm text-red-600">{errors.matches}</p>
        )}
        {matches.length < matchesPerRound && (
          <Button type="button" variant="link" onClick={addMatch} disabled={disabled}>
            + Добавить матч
          </Button>
        )}
      </div>

      <Button type="submit" disabled={disabled || submitting}>
        {isEditing ? "Сохранить черновик" : "Создать черновик тура"}
      </Button>
    </form>
  );
}
