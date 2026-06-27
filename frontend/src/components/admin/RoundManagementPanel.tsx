"use client";

import { useEffect, useMemo, useState } from "react";
import { deriveAdminUiMode } from "@/lib/admin/deriveAdminUiMode";
import {
  canChangeDeadline,
  deadlineChangeClosedMessage,
  deadlineErrorMessage,
  earliestMatchTime,
  getDeadlineRuleHours,
  isDeadlineValid,
} from "@/lib/admin/deadlineRule";
import {
  formatDateTimeRu,
  fromDatetimeLocal,
  roundStatusLabel,
  toDatetimeLocal,
} from "@/lib/admin/format";
import { RoundBuilderForm } from "@/components/admin/RoundBuilderForm";
import { RoundPhasePanel } from "@/components/admin/RoundPhasePanel";
import {
  MatchEditorRow,
  matchActionDialogCopy,
  type MatchRowAction,
} from "@/components/admin/MatchEditorRow";
import { RoundStatusSidebar } from "@/components/admin/RoundStatusSidebar";
import { FreeTourModal } from "@/components/admin/FreeTourModal";
import { NewsletterPromptModal } from "@/components/admin/NewsletterPromptModal";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { LoadingState } from "@/components/ui/LoadingState";
import { useAuth } from "@/hooks/useAuth";
import type { ContestOut, MatchOut, MatchStatus, RoundOut, TeamOut } from "@/types/api";

function teamIdByName(teams: TeamOut[], name: string): number | undefined {
  return teams.find((t) => t.name === name || t.short_name === name)?.id;
}

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
    body: {
      deadline?: string;
      matches?: {
        match_id: number;
        team1_id?: number;
        team2_id?: number;
        date_time?: string;
        status?: string;
      }[];
    },
  ) => Promise<void>;
  onCreateFreeTour: (data: {
    deadline: string;
    matches: { match_id: number; new_date_time: string }[];
  }) => Promise<void>;
  onCloseRound?: (roundId: number) => Promise<void>;
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
  onCloseRound,
  onRefetchMatches,
  refetchContest,
}: RoundManagementPanelProps) {
  const { user } = useAuth();
  const isAdmin = user?.role === "ADMIN";
  const selectedRound = rounds.find((r) => r.id === selectedRoundId) ?? null;
  const hasDraft = rounds.some((r) => r.status === "DRAFT");
  const atRoundCap = rounds.length >= contest.total_rounds;

  const uiMode = deriveAdminUiMode({
    contest,
    round: selectedRound,
    matches,
    deadlinePassed,
    hasDraftRound: hasDraft,
  });

  const [localMatches, setLocalMatches] = useState<MatchOut[]>(matches);
  const [deadlineEdit, setDeadlineEdit] = useState("");
  const [showActivate, setShowActivate] = useState(false);
  const [showFreeTour, setShowFreeTour] = useState(false);
  const [showNewsletter, setShowNewsletter] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showDraftEdit, setShowDraftEdit] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [closing, setClosing] = useState(false);
  const [pendingMatchAction, setPendingMatchAction] = useState<{
    action: MatchRowAction;
    match: MatchOut;
  } | null>(null);
  const [actionSaving, setActionSaving] = useState(false);

  useEffect(() => {
    setLocalMatches(matches);
    if (selectedRound) setDeadlineEdit(toDatetimeLocal(selectedRound.deadline));
    setShowDraftEdit(false);
    setSaveError(null);
  }, [matches, selectedRound]);

  const ruleHours = getDeadlineRuleHours(contest.rules_json);
  const earliest = earliestMatchTime(localMatches);
  const deadlineIso = deadlineEdit ? fromDatetimeLocal(deadlineEdit) : "";
  const deadlinePlacementValid =
    !deadlineEdit || earliest === null
      ? true
      : isDeadlineValid(deadlineIso, new Date(earliest).toISOString());
  const changeWindowOpen =
    selectedRound?.status === "ACTIVE" && selectedRound?.deadline != null
      ? canChangeDeadline(new Date(), selectedRound.deadline, ruleHours)
      : true; // DRAFT: no lockout
  const deadlineValid = deadlinePlacementValid;
  const deadlineChangeBlocked = selectedRound?.status === "ACTIVE" && !changeWindowOpen;
  const deadlineDirty =
    selectedRound != null && deadlineEdit !== toDatetimeLocal(selectedRound.deadline);
  const saveDisabled =
    saving ||
    (deadlineDirty &&
      (!deadlineValid || deadlineChangeBlocked || !uiMode.canEditDeadline));

  const nextRoundNumber = useMemo(() => {
    if (!rounds.length) return 1;
    return Math.max(...rounds.map((r) => r.number)) + 1;
  }, [rounds]);

  const handleMatchActionConfirm = async () => {
    if (!pendingMatchAction || !selectedRound) return;
    const { action, match } = pendingMatchAction;
    const status: MatchStatus =
      action === "cancel" ? "CANCELED" : action === "postpone" ? "POSTPONED" : "SCHEDULED";
    setActionSaving(true);
    try {
      await onUpdateRound(selectedRound.id, {
        matches: [{ match_id: match.id, status }],
      });
      setLocalMatches((prev) =>
        prev.map((row) => (row.id === match.id ? { ...row, status } : row)),
      );
      await onRefetchMatches();
      if (action === "postpone") setShowFreeTour(true);
    } finally {
      setActionSaving(false);
      setPendingMatchAction(null);
    }
  };

  const handleCloseRound = async () => {
    if (!selectedRound || !onCloseRound) return;
    setClosing(true);
    try {
      await onCloseRound(selectedRound.id);
      await onRefetchMatches();
    } finally {
      setClosing(false);
    }
  };

  const handleSaveActive = async () => {
    if (!selectedRound) return;
    const missingMatchDate = localMatches.some((m) => !m.date_time?.trim());
    if (missingMatchDate) {
      setSaveError("Укажите дату и время для каждого матча");
      return;
    }
    setSaveError(null);
    setSaving(true);
    try {
      const body: {
        deadline?: string;
        matches?: {
          match_id: number;
          team1_id?: number;
          team2_id?: number;
          date_time?: string;
          status?: string;
        }[];
      } = {
        matches: localMatches.map((m) => ({
          match_id: m.id,
          ...(uiMode.canEditRoundStructure
            ? {
                team1_id: m.team1_id ?? teamIdByName(teams, m.team1),
                team2_id: m.team2_id ?? teamIdByName(teams, m.team2),
              }
            : {}),
          date_time: m.date_time,
          status: m.status,
        })),
      };
      if (deadlineEdit && deadlineValid && !deadlineChangeBlocked && uiMode.canEditDeadline) {
        body.deadline = deadlineIso;
      }
      await onUpdateRound(selectedRound.id, body);
      await onRefetchMatches();
      if (deadlineEdit && deadlineValid && !deadlineChangeBlocked) setShowNewsletter(true);
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

  // create button disabled state
  const createDisabled = uiMode.disableAllMutations || atRoundCap || hasDraft;
  const createTooltip = atRoundCap
    ? `Достигнут лимит туров (${contest.total_rounds}) из настроек конкурса`
    : hasDraft
      ? "Сначала активируйте или удалите черновик тура"
      : undefined;

  if (loading && !rounds.length) return <LoadingState message="Загрузка туров…" />;

  // Determine if selected round is in a "phase" (CLOSED/CALCULATED/PUBLISHED)
  const isPhaseRound =
    selectedRound?.status === "CLOSED" ||
    selectedRound?.status === "CALCULATED" ||
    selectedRound?.status === "PUBLISHED";

  // DRAFT edit data
  const draftInitialValues =
    selectedRound?.status === "DRAFT"
      ? {
          number: selectedRound.number,
          deadline: selectedRound.deadline,
          matches: localMatches.map((m) => ({
            team1_id: m.team1_id ?? teamIdByName(teams, m.team1) ?? 0,
            team2_id: m.team2_id ?? teamIdByName(teams, m.team2) ?? 0,
            date_time: toDatetimeLocal(m.date_time),
          })),
        }
      : undefined;

  return (
    <div className="space-y-6">
      {/* Selector row — "Тур" select + «+ Создать тур» always beside it (§10.2) */}
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

        {/* «+ Создать тур» always visible, disabled at cap / draft (§10.2) */}
        {!uiMode.disableAllMutations && (
          <button
            type="button"
            disabled={createDisabled}
            title={createTooltip}
            onClick={() => setShowCreateForm((v) => !v)}
            className="px-3 py-1 text-sm text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            + Создать тур
          </button>
        )}

        {/* «+ Добавить свободный тур» as secondary link */}
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

      {/* Create form (toggled by «+ Создать тур» button) */}
      {showCreateForm && !createDisabled && (
        <section>
          <RoundBuilderForm
            teams={teams}
            matchesPerRound={contest.matches_per_round}
            rules={contest.rules_json}
            nextRoundNumber={nextRoundNumber}
            disabled={!uiMode.canCreateRound}
            onSubmit={async (data) => {
              await onCreateRound(data);
              setShowCreateForm(false);
            }}
          />
        </section>
      )}

      {selectedRound && (
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-6">
          <div>
            {/* Phase panels: CLOSED / CALCULATED / PUBLISHED */}
            {isPhaseRound ? (
              <section className="border border-gray-200 rounded-lg p-4">
                <div className="flex flex-wrap justify-between items-center gap-2 mb-4">
                  <h3 className="font-semibold text-gray-900">
                    Тур {selectedRound.number} — {roundStatusLabel(selectedRound.status)}
                  </h3>
                  {selectedRound.status === "PUBLISHED" && (
                    <span className="text-sm font-medium text-green-700 bg-green-50 px-2 py-1 rounded">
                      Применено
                    </span>
                  )}
                </div>
                <RoundPhasePanel contest={contest} round={selectedRound} matches={localMatches} />
              </section>
            ) : (
              /* DRAFT and ACTIVE panels */
              <section className="border border-gray-200 rounded-lg p-4">
                <div className="flex flex-wrap justify-between items-center gap-2 mb-4">
                  <h3 className="font-semibold text-gray-900">
                    Тур {selectedRound.number} — {roundStatusLabel(selectedRound.status)}
                  </h3>
                  {/* DRAFT: Редактировать / Активировать */}
                  {selectedRound.status === "DRAFT" && !uiMode.disableAllMutations && (
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => setShowDraftEdit((v) => !v)}
                        className="px-3 py-1.5 text-sm border border-gray-300 rounded hover:bg-gray-50"
                      >
                        {showDraftEdit ? "Свернуть" : "Редактировать"}
                      </button>
                      <button
                        type="button"
                        onClick={() => setShowActivate(true)}
                        className="px-4 py-2 text-sm text-white bg-green-600 rounded hover:bg-green-700"
                      >
                        Активировать
                      </button>
                    </div>
                  )}
                </div>

                {/* DRAFT inline editor (F10) */}
                {selectedRound.status === "DRAFT" && showDraftEdit && (
                  <div className="mb-4">
                    <RoundBuilderForm
                      teams={teams}
                      matchesPerRound={contest.matches_per_round}
                      rules={contest.rules_json}
                      nextRoundNumber={selectedRound.number}
                      initialValues={draftInitialValues}
                      onSubmit={async (data) => {
                        await onUpdateRound(selectedRound.id, {
                          deadline: data.deadline,
                          matches: data.matches.map((m, i) => ({
                            match_id: localMatches[i]?.id ?? 0,
                            team1_id: m.team1_id,
                            team2_id: m.team2_id,
                            date_time: m.date_time,
                          })),
                        });
                        setShowDraftEdit(false);
                        await onRefetchMatches();
                      }}
                    />
                  </div>
                )}

                {/* ACTIVE: phase-aware hints */}
                {selectedRound.status === "ACTIVE" && (
                  <p className="text-sm text-blue-700 bg-blue-50 border border-blue-200 rounded px-3 py-2 mb-3">
                    Тур активен. Состав матчей изменить нельзя. До начала матча можно перенести
                    время; отмена — в любой момент. Перенос на другую неделю — статус «Перенесён»
                    и свободный тур.
                  </p>
                )}

                {/* Deadline editor (hidden in DRAFT inline edit — form has its own field) */}
                {(selectedRound.status === "DRAFT" || selectedRound.status === "ACTIVE") &&
                  !(selectedRound.status === "DRAFT" && showDraftEdit) && (
                  <div className="mb-4 max-w-xs">
                    <label className="block text-sm text-gray-700 mb-1">Дедлайн прогнозов</label>
                    <input
                      type="datetime-local"
                      value={deadlineEdit}
                      onChange={(e) => setDeadlineEdit(e.target.value)}
                      disabled={!uiMode.canEditDeadline || uiMode.roundEditorReadonly}
                      className="w-full border border-gray-300 rounded px-3 py-2 text-sm disabled:bg-gray-100"
                    />
                    {!deadlinePlacementValid && (
                      <p className="text-sm text-red-600 mt-1">{deadlineErrorMessage()}</p>
                    )}
                    {deadlineChangeBlocked && (
                      <p className="text-sm text-amber-600 mt-1">
                        {deadlineChangeClosedMessage(ruleHours)}
                      </p>
                    )}
                  </div>
                )}

                {/* Match table (DRAFT full or ACTIVE depending on phase) */}
                {selectedRound.status !== "DRAFT" || !showDraftEdit ? (
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
                            roundStatus={selectedRound.status}
                            isAdmin={isAdmin}
                            teams={teams}
                            canEditStructure={uiMode.canEditRoundStructure}
                            canEditStatusAndDate={uiMode.canEditMatchStatusAndDate}
                            onRequestAction={(action, match) =>
                              setPendingMatchAction({ action, match })
                            }
                            onChange={(patch) => {
                              setSaveError(null);
                              setLocalMatches((prev) =>
                                prev.map((row) => (row.id === m.id ? { ...row, ...patch } : row)),
                              );
                            }}
                          />
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : null}

                {saveError && (
                  <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2 mt-4">
                    {saveError}
                  </p>
                )}

                {(selectedRound.status === "ACTIVE" || selectedRound.status === "DRAFT") &&
                  !uiMode.disableAllMutations &&
                  selectedRound.status !== "DRAFT" && (
                    <button
                      type="button"
                      onClick={handleSaveActive}
                      disabled={saveDisabled}
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
          </div>

          <RoundStatusSidebar
            contest={contest}
            round={selectedRound}
            matches={localMatches}
            deadlinePassed={deadlinePassed}
            disableAllMutations={uiMode.disableAllMutations}
            onCloseRound={onCloseRound ? handleCloseRound : undefined}
            closing={closing}
          />
        </div>
      )}

      {/* Activate confirm */}
      <ConfirmDialog
        open={showActivate}
        title="Активировать тур?"
        message="После активации участники смогут делать прогнозы. Состав матчей изменить уже нельзя — только перенос времени до начала, отмена или перенос в свободный тур."
        confirmLabel="Активировать"
        onConfirm={handleActivate}
        onCancel={() => setShowActivate(false)}
      />

      {pendingMatchAction && (
        <ConfirmDialog
          open
          {...matchActionDialogCopy(pendingMatchAction.action, pendingMatchAction.match)}
          onConfirm={() => void handleMatchActionConfirm()}
          onCancel={() => !actionSaving && setPendingMatchAction(null)}
        />
      )}

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
