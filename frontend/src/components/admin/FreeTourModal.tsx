"use client";

import { useEffect, useState } from "react";
import { collectPostponedMatches, type PostponedMatchItem } from "@/lib/admin/collectPostponedMatches";
import { formatDateTimeRu, fromDatetimeLocal } from "@/lib/admin/format";
import { freeTourSchema } from "@/lib/validation/admin";
import { LoadingState } from "@/components/ui/LoadingState";

interface FreeTourModalProps {
  open: boolean;
  contestId: number;
  onClose: () => void;
  onSubmit: (data: {
    deadline: string;
    matches: { match_id: number; new_date_time: string }[];
  }) => Promise<void>;
}

export function FreeTourModal({ open, contestId, onClose, onSubmit }: FreeTourModalProps) {
  const [postponed, setPostponed] = useState<PostponedMatchItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [dates, setDates] = useState<Record<number, string>>({});
  const [deadline, setDeadline] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    void collectPostponedMatches(contestId)
      .then(setPostponed)
      .finally(() => setLoading(false));
  }, [open, contestId]);

  if (!open) return null;

  const toggle = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const matches = Array.from(selected).map((match_id) => ({
      match_id,
      new_date_time: fromDatetimeLocal(dates[match_id] ?? ""),
    }));
    const parsed = freeTourSchema.safeParse({
      deadline: deadline ? fromDatetimeLocal(deadline) : "",
      matches,
    });
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? "Ошибка валидации");
      return;
    }
    setSubmitting(true);
    try {
      await onSubmit(parsed.data);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-lg shadow-lg max-w-2xl w-full p-6 max-h-[90vh] overflow-y-auto">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Свободный тур</h3>
        <p className="text-sm text-gray-600 mb-4">
          Выберите перенесённые матчи и укажите новые даты.
        </p>
        {loading ? (
          <LoadingState message="Загрузка перенесённых матчей…" />
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2 max-h-60 overflow-y-auto">
              {postponed.map((m) => (
                <label
                  key={m.id}
                  className="flex flex-wrap items-center gap-2 border border-gray-200 rounded p-2 text-sm"
                >
                  <input
                    type="checkbox"
                    checked={selected.has(m.id)}
                    onChange={() => toggle(m.id)}
                  />
                  <span>
                    {m.team1} — {m.team2} (тур {m.roundNumber})
                  </span>
                  <span className="text-gray-500">{formatDateTimeRu(m.date_time)}</span>
                  {selected.has(m.id) && (
                    <input
                      type="datetime-local"
                      value={dates[m.id] ?? ""}
                      onChange={(e) =>
                        setDates((prev) => ({ ...prev, [m.id]: e.target.value }))
                      }
                      className="border border-gray-300 rounded px-2 py-1"
                      required
                    />
                  )}
                </label>
              ))}
              {!postponed.length && (
                <p className="text-gray-500 text-sm">Нет перенесённых матчей</p>
              )}
            </div>
            <div>
              <label className="block text-sm text-gray-700 mb-1">Дедлайн тура</label>
              <input
                type="datetime-local"
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
                className="border border-gray-300 rounded px-3 py-2 text-sm"
                required
              />
            </div>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm border border-gray-300 rounded hover:bg-gray-50"
              >
                Отмена
              </button>
              <button
                type="submit"
                disabled={submitting || !postponed.length}
                className="px-4 py-2 text-sm text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50"
              >
                Создать свободный тур
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
