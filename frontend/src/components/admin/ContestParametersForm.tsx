"use client";

import { useState, type FormEvent } from "react";
import { contestParametersSchema } from "@/lib/validation/admin";
import type { ZodIssue } from "zod";
import type { ContestOut } from "@/types/api";
import { RulesDisplayPanel } from "@/components/admin/RulesDisplayPanel";
import { ContestLifecycleActions } from "@/components/admin/ContestLifecycleActions";

interface ContestParametersFormProps {
  contest: ContestOut;
  readonly: boolean;
  onSave: (data: {
    total_teams: number;
    matches_per_round: number;
    total_rounds: number;
    is_round_robin: boolean;
  }) => Promise<void>;
  onLifecycleSuccess: () => Promise<void>;
  onLifecycleError: (message: string) => void;
}

export function ContestParametersForm({
  contest,
  readonly,
  onSave,
  onLifecycleSuccess,
  onLifecycleError,
}: ContestParametersFormProps) {
  const [totalTeams, setTotalTeams] = useState(contest.total_teams);
  const [matchesPerRound, setMatchesPerRound] = useState(contest.matches_per_round);
  const [totalRounds, setTotalRounds] = useState(contest.total_rounds);
  const [isRoundRobin, setIsRoundRobin] = useState(contest.is_round_robin);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (readonly) return;
    setErrors({});
    const parsed = contestParametersSchema.safeParse({
      total_teams: totalTeams,
      matches_per_round: matchesPerRound,
      total_rounds: totalRounds,
      is_round_robin: isRoundRobin,
    });
    if (!parsed.success) {
      const next: Record<string, string> = {};
      parsed.error.issues.forEach((i: ZodIssue) => {
        next[String(i.path[0])] = i.message;
      });
      setErrors(next);
      return;
    }
    setSubmitting(true);
    try {
      await onSave(parsed.data);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <form onSubmit={handleSubmit} className="space-y-6 pb-24">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-2xl">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Команд</label>
            <input
              type="number"
              value={totalTeams}
              onChange={(e) => setTotalTeams(Number(e.target.value))}
              disabled={readonly}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm disabled:bg-gray-100"
            />
            {errors.total_teams && <p className="text-sm text-red-600">{errors.total_teams}</p>}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Матчей в туре</label>
            <input
              type="number"
              value={matchesPerRound}
              onChange={(e) => setMatchesPerRound(Number(e.target.value))}
              disabled={readonly}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm disabled:bg-gray-100"
            />
            {errors.matches_per_round && (
              <p className="text-sm text-red-600">{errors.matches_per_round}</p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Туров</label>
            <input
              type="number"
              value={totalRounds}
              onChange={(e) => setTotalRounds(Number(e.target.value))}
              disabled={readonly}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm disabled:bg-gray-100"
            />
            {errors.total_rounds && <p className="text-sm text-red-600">{errors.total_rounds}</p>}
          </div>
          <div className="flex items-center gap-2 pt-6">
            <input
              id="round-robin"
              type="checkbox"
              checked={!isRoundRobin}
              onChange={(e) => setIsRoundRobin(!e.target.checked)}
              disabled={readonly}
            />
            <label htmlFor="round-robin" className="text-sm text-gray-700">
              Произвольное количество
            </label>
          </div>
        </div>

        <RulesDisplayPanel rulesJson={contest.rules_json as Record<string, unknown>} />

        {!readonly && (
          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-2 text-sm text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50"
          >
            Сохранить параметры
          </button>
        )}
      </form>

      <ContestLifecycleActions
        contest={contest}
        onSuccess={onLifecycleSuccess}
        onError={onLifecycleError}
      />
    </>
  );
}
