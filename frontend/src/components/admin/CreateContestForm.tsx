"use client";

import { useState, type FormEvent } from "react";
import { createContestSchema } from "@/lib/validation/admin";

interface CreateContestFormProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: {
    name: string;
    slug?: string;
    total_teams: number;
    matches_per_round: number;
    total_rounds: number;
    is_round_robin: boolean;
  }) => Promise<void>;
}

export function CreateContestForm({ open, onClose, onSubmit }: CreateContestFormProps) {
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [totalTeams, setTotalTeams] = useState(8);
  const [matchesPerRound, setMatchesPerRound] = useState(4);
  const [totalRounds, setTotalRounds] = useState(14);
  const [isRoundRobin, setIsRoundRobin] = useState(true);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  if (!open) return null;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setErrors({});
    const parsed = createContestSchema.safeParse({
      name,
      slug: slug || undefined,
      total_teams: totalTeams,
      matches_per_round: matchesPerRound,
      total_rounds: totalRounds,
      is_round_robin: isRoundRobin,
    });
    if (!parsed.success) {
      const next: Record<string, string> = {};
      parsed.error.issues.forEach((i) => {
        next[String(i.path[0])] = i.message;
      });
      setErrors(next);
      return;
    }
    setSubmitting(true);
    try {
      await onSubmit(parsed.data);
      onClose();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-lg shadow-lg max-w-lg w-full p-6 max-h-[90vh] overflow-y-auto">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Новый конкурс</h3>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Название</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
            />
            {errors.name && <p className="text-sm text-red-600">{errors.name}</p>}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Slug (необязательно)
            </label>
            <input
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
            />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-gray-600 mb-1">Команд</label>
              <input
                type="number"
                value={totalTeams}
                onChange={(e) => setTotalTeams(Number(e.target.value))}
                className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">Матчей/тур</label>
              <input
                type="number"
                value={matchesPerRound}
                onChange={(e) => setMatchesPerRound(Number(e.target.value))}
                className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">Туров</label>
              <input
                type="number"
                value={totalRounds}
                onChange={(e) => setTotalRounds(Number(e.target.value))}
                className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
              />
            </div>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={isRoundRobin}
              onChange={(e) => setIsRoundRobin(e.target.checked)}
            />
            Круговая система
          </label>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm border border-gray-300 rounded hover:bg-gray-50"
            >
              Отмена
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 text-sm text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50"
            >
              Создать
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
