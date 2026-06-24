"use client";

import { useEffect, useMemo, useState } from "react";
import { deriveAdminUiMode } from "@/lib/admin/deriveAdminUiMode";
import {
  deadlineErrorMessage,
  earliestMatchTime,
  getDeadlineRuleHours,
  isDeadlineValid,
} from "@/lib/admin/deadlineRule";
import { formatDateTimeRu, fromDatetimeLocal, roundStatusLabel, toDatetimeLocal } from "@/lib/admin/format";
import type { ContestOut, MatchOut, RoundOut, TeamOut } from "@/types/api";
import { RoundBuilderForm } from "@/components/admin/RoundBuilderForm";
import { MatchEditorRow } from "@/components/admin/MatchEditorRow";
import { FreeTourModal } from "@/components/admin/FreeTourModal";
import { NewsletterPromptModal } from "@/components/admin/NewsletterPromptModal";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { LoadingState } from "@/components/ui/LoadingState";

interface RoundManagementPanelProps {
  contest: ContestOut;
  rounds: RoundOut[];
  teams: TeamOut[];
  selectedRoundId: number | null;
  matches: MatchOut[];
  deadlinePassed: boolean;
  loading: boolean;
  onSelectRound: (id: number) => void;
  onCreateRound: (data: {
    number: number;
    deadline: string;
    matches: { team1_id: number; team2_id: number; date_time: string }[];
  }) => Promise<void>;
  onActivate: (roundId: number) => Promise<void>;
  onUpdateRound: (
    roundId: number,
    body: { deadline?: string; matches?: { match_id: number; date_time?: string; status?: string }[] },
  ) => Promise<void>;
  onCreateFreeTour: (data: {
    deadline: string;
    matches: { match_id: number; new_date_time: string }[];
  }) => Promise<void>;
  onRefetchMatches: () => Promise<void>;
  refetchContest: () => Promise<void>;
}

export function RoundManagementPanel({
  contest,
  rounds,
  teams,
  selectedRoundId,
  matches,
  deadlinePassed,
  loading,
  onSelectRound,
  onCreateRound,
  onActivate,
  onUpdateRound,
  onCreateFreeTour,
  onRefetchMatches,
  refetchContest,
}: RoundManagementPanelProps) {
  const selectedRound = rounds.find((r) => r.id === selectedRoundId) ?? null;
  const uiMode = deriveAdminUiMode({
    contest,
    round: selectedRound,
    matches,
    deadlinePassed,
  });

  const [localMatches, setLocalMatches] = useState<MatchOut[]>(matches);
  const [deadlineEdit, setDeadlineEdit] = useState("");
  const [showActivate, setShowActivate] = useState(false);
  const [showFreeTour, setShowFreeTour] = useState(false);
  const [showNewsletter, setShowNewsletter] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setLocalMatches(matches);
    if (selectedRound) setDeadlineEdit(toDatetimeLocal(selectedRound.deadline));
  }, [matches, selectedRound]);

  const ruleHours = getDeadlineRuleHours(contest.rules_json);
  const earliest = earliestMatchTime(localMatches);
  const deadlineIso = deadlineEdit ? fromDatetimeLocal(deadlineEdit) : "";
  const deadlineValid =
    !deadlineEdit || earliest === null
      ? true
      : isDeadlineValid(deadlineIso, new Date(earliest).toISOString(), ruleHours);

  const nextRoundNumber = useMemo(() => {
    if (!rounds.length) return 1;
    return Math.max(...rounds.map((r) => r.number)) + 1;
  }, [rounds]);

  const hasDraft = rounds.some((r) => r.status === "DRAFT");

  const handleSaveActive = async () => {
    if (!selectedRound) return;
    setSaving(true);
    try {
      const body: {
        deadline?: string;
        matches?: { match_id: number; date_time?: string; status?: string }[];
      } = {
        matches: localMatches.map((m) => ({
          match_id: m.id,
          date_time: m.date_time,
          status: m.status,
        })),
      };
      if (deadlineEdit && deadlineValid) {
        body.deadline = deadlineIso;
      }
      await onUpdateRound(selectedRound.id, body);
      await onRefetchMatches();
      if (deadlineEdit && deadlineValid) setShowNewsletter(true);
    } finally {
      setSaving(false);
    }
  };

  const handleActivate = async () => {
    if (!selectedRound) return;
    await onActivate(selectedRound.id);
    await refetchContest();
    setShowActivate(false);
  };

  if (loading && !rounds.length) return <LoadingState message="Загрузка туров…" />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <label className="text-sm text-gray-700">Тур:</label>
        <select
          value={selectedRoundId ?? ""}
          onChange={(e) => onSelectRound(Number(e.target.value))}
          className="border border-gray-300 rounded px-3 py-1 text-sm"
        >
          <option value="">Выберите тур</option>
          {rounds.map((r) => (
            <option key={r.id} value={r.id}>
              Тур {r.number} — {roundStatusLabel(r.status)}
            </option>
          ))}
        </select>
        {!uiMode.disableAllMutations && !hasDraft && (
          <button
            type="button"
            onClick={() => setShowFreeTour(true)}
            className="text-sm text-blue-600 hover:underline"
          >
            + Добавить свободный тур
          </button>
        )}
      </div>

      {uiMode.showActiveRoundHint && (
        <p className="text-sm text-blue-700 bg-blue-50 border border-blue-200 rounded px-3 py-2">
          ТУР АКТИВИРОВАН. Менять можно только статус матча и дату.
        </p>
      )}
      {uiMode.showDeadlinePassedHint && (
        <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2">
          Дедлайн прошел. Менять команды нельзя. Только статус и дату.
        </p>
      )}

      {uiMode.canEditRoundStructure && !hasDraft && (
        <RoundBuilderForm
          teams={teams}
          matchesPerRound={contest.matches_per_round}
          rules={contest.rules_json}
          nextRoundNumber={nextRoundNumber}
          disabled={uiMode.disableAllMutations}
          onSubmit={onCreateRound}
        />
      )}

      {selectedRound && (
        <section className="border border-gray-200 rounded-lg p-4">
          <div className="flex flex-wrap justify-between items-center gap-2 mb-4">
            <h3 className="font-semibold text-gray-900">
              Тур {selectedRound.number} — {roundStatusLabel(selectedRound.status)}
            </h3>
            {selectedRound.status === "DRAFT" && !uiMode.disableAllMutations && (
              <button
                type="button"
                onClick={() => setShowActivate(true)}
                className="px-4 py-2 text-sm text-white bg-green-600 rounded hover:bg-green-700"
              >
                Активировать
              </button>
            )}
          </div>

          {(selectedRound.status === "DRAFT" || selectedRound.status === "ACTIVE") && (
            <div className="mb-4 max-w-xs">
              <label className="block text-sm text-gray-700 mb-1">Дедлайн прогнозов</label>
              <input
                type="datetime-local"
                value={deadlineEdit}
                onChange={(e) => setDeadlineEdit(e.target.value)}
                disabled={!uiMode.canEditDeadline || uiMode.roundEditorReadonly}
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm disabled:bg-gray-100"
              />
              {!deadlineValid && (
                <p className="text-sm text-red-600 mt-1">{deadlineErrorMessage(ruleHours)}</p>
              )}
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left">Матч</th>
                  <th className="px-3 py-2 text-left">Дата</th>
                  <th className="px-3 py-2 text-left">Статус</th>
                </tr>
              </thead>
              <tbody>
                {localMatches.map((m) => (
                  <MatchEditorRow
                    key={m.id}
                    match={m}
                    canEditStructure={uiMode.canEditRoundStructure}
                    canEditStatusAndDate={uiMode.canEditMatchStatusAndDate}
                    onChange={(patch) => {
                      setLocalMatches((prev) =>
                        prev.map((row) => (row.id === m.id ? { ...row, ...patch } : row)),
                      );
                    }}
                  />
                ))}
              </tbody>
            </table>
          </div>

          {(selectedRound.status === "ACTIVE" || selectedRound.status === "DRAFT") &&
            !uiMode.disableAllMutations && (
              <button
                type="button"
                onClick={handleSaveActive}
                disabled={saving || !deadlineValid}
                className="mt-4 px-4 py-2 text-sm text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50"
              >
                Сохранить изменения
              </button>
            )}

          {selectedRound.deadline && (
            <p className="text-xs text-gray-500 mt-2">
              Текущий дедлайн: {formatDateTimeRu(selectedRound.deadline)}
            </p>
          )}
        </section>
      )}

      <ConfirmDialog
        open={showActivate}
        title="Активировать тур?"
        message="После активации редактирование структуры тура будет запрещено"
        confirmLabel="Активировать"
        onConfirm={handleActivate}
        onCancel={() => setShowActivate(false)}
      />

      <FreeTourModal
        open={showFreeTour}
        contestId={contest.id}
        onClose={() => setShowFreeTour(false)}
        onSubmit={async (data) => {
          await onCreateFreeTour(data);
          setShowFreeTour(false);
        }}
      />

      <NewsletterPromptModal open={showNewsletter} onClose={() => setShowNewsletter(false)} />
    </div>
  );
}
