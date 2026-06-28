"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { PredictionMatchRow } from "@/components/predictions/PredictionMatchRow";
import { DeadlineCountdown } from "@/components/predictions/DeadlineCountdown";
import { DeadlineWarningBanner } from "@/components/predictions/DeadlineWarningBanner";
import { useDeadline } from "@/hooks/useDeadline";
import { useMaxScore } from "@/hooks/useMaxScore";
import { usePredictionSubmit } from "@/hooks/usePredictionSubmit";
import { shouldShowDeadlineWarning } from "@/lib/privacy/deadlineWarning";
import {
  buildPredictionBatch,
  countFilledMatches,
  predictionBatchSchema,
  type MatchScoreState,
} from "@/lib/validation/prediction";
import type { MatchOut, PredictionEntryOut, RoundOut } from "@/types/api";

interface PredictionFormProps {
  contestId: number;
  round: RoundOut;
  matches: MatchOut[];
  entries: PredictionEntryOut[];
  deadlinePassed: boolean;
  userId: number;
  matchesPerRound: number;
  contestPaused?: boolean;
  onSaved: () => void;
}

function initFormFromEntries(
  matches: MatchOut[],
  entries: PredictionEntryOut[],
  userId: number,
): Record<number, MatchScoreState> {
  const own = entries.find((e) => e.user_id === userId);
  const form: Record<number, MatchScoreState> = {};
  for (const m of matches) {
    const pred = own?.predictions?.find((p) => p.match_id === m.id);
    if (pred && pred.score1 != null && pred.score2 != null) {
      form[m.id] = { score1: pred.score1, score2: pred.score2 };
    } else {
      form[m.id] = {};
    }
  }
  return form;
}

export function PredictionForm({
  contestId,
  round,
  matches,
  entries,
  deadlinePassed,
  userId,
  matchesPerRound,
  contestPaused = false,
  onSaved,
}: PredictionFormProps) {
  const maxScore = useMaxScore();
  const { submit, submitting } = usePredictionSubmit(contestId, round.id);
  const deadline = useDeadline(round, deadlinePassed);

  const [form, setForm] = useState<Record<number, MatchScoreState>>(() =>
    initFormFromEntries(matches, entries, userId),
  );
  const [editing, setEditing] = useState(() => {
    const own = entries.find((e) => e.user_id === userId);
    return !own?.submitted;
  });

  useEffect(() => {
    setForm(initFormFromEntries(matches, entries, userId));
    const own = entries.find((e) => e.user_id === userId);
    setEditing(!own?.submitted);
  }, [matches, entries, userId]);

  const matchIds = useMemo(() => matches.map((m) => m.id), [matches]);
  const filledCount = countFilledMatches(form, matchIds);
  const batchComplete = filledCount === matchesPerRound && matchIds.length === matchesPerRound;

  const readonly =
    deadline.deadlinePassed ||
    deadlinePassed ||
    round.status !== "ACTIVE" ||
    contestPaused ||
    !editing;

  const hasOutOfRange = useMemo(() => {
    for (const id of matchIds) {
      const cell = form[id];
      if (cell?.score1 !== undefined && (cell.score1 < 0 || cell.score1 > maxScore)) return true;
      if (cell?.score2 !== undefined && (cell.score2 < 0 || cell.score2 > maxScore)) return true;
    }
    return false;
  }, [form, matchIds, maxScore]);

  const updateScore = useCallback(
    (matchId: number, field: "score1" | "score2", val: number | "") => {
      setForm((prev) => ({
        ...prev,
        [matchId]: { ...prev[matchId], [field]: val === "" ? undefined : val },
      }));
    },
    [],
  );

  const handleSave = async () => {
    const batch = buildPredictionBatch(form, matchIds);
    const parsed = predictionBatchSchema(maxScore, matchesPerRound).safeParse({
      predictions: batch,
    });
    if (!parsed.success) return;

    const ok = await submit(parsed.data);
    if (ok) {
      setEditing(false);
      onSaved();
    }
  };

  const showWarning = !deadline.deadlinePassed && shouldShowDeadlineWarning(deadline.secondsLeft);

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
      {deadline.deadlinePassed ? (
        <p className="text-sm font-medium text-gray-700" data-testid="deadline-countdown">
          Дедлайн прошёл
        </p>
      ) : (
        <DeadlineCountdown label={deadline.label} />
      )}

      {showWarning && <DeadlineWarningBanner />}

      {contestPaused && (
        <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2">
          Конкурс приостановлен — прогнозы временно недоступны
        </p>
      )}

      {round.status !== "ACTIVE" && !deadlinePassed && (
        <p className="text-sm text-gray-600">Тур не активен — прогнозы недоступны</p>
      )}

      <div className="divide-y divide-gray-100">
        {matches.map((match) => {
          const cell = form[match.id] ?? {};
          return (
            <PredictionMatchRow
              key={match.id}
              match={match}
              score1={cell.score1 ?? ""}
              score2={cell.score2 ?? ""}
              maxScore={maxScore}
              readonly={readonly}
              onScore1Change={(v) => updateScore(match.id, "score1", v)}
              onScore2Change={(v) => updateScore(match.id, "score2", v)}
            />
          );
        })}
      </div>

      {!batchComplete && editing && !readonly && (
        <p className="text-sm text-gray-500">Заполните прогнозы на все матчи тура</p>
      )}

      <div className="flex gap-3 pt-2">
        {editing ? (
          <button
            type="button"
            onClick={handleSave}
            disabled={!batchComplete || submitting || readonly || hasOutOfRange}
            className="bg-blue-600 text-white rounded px-4 py-2 text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Сохранить прогноз
          </button>
        ) : (
          <button
            type="button"
            onClick={() => setEditing(true)}
            disabled={
              deadline.deadlinePassed ||
              deadlinePassed ||
              round.status !== "ACTIVE" ||
              contestPaused
            }
            className="border border-gray-300 rounded px-4 py-2 text-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Редактировать
          </button>
        )}
      </div>
    </div>
  );
}
