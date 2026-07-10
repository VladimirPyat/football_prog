"use client";

import { useEffect, useMemo, useState } from "react";
import { deriveAdminUiMode } from "@/lib/admin/deriveAdminUiMode";
import {
  effectiveRoundStatus,
  isDeadlinePassedNow,
  isPhaseRoundStatus,
} from "@/lib/admin/roundEffectiveStatus";
import {
  canChangeDeadline,
  deadlineChangeClosedMessage,
  deadlineErrorMessage,
  earliestMatchTime,
  getDeadlineRuleHours,
  isDeadlinePlacementValid,
} from "@/lib/admin/deadlineRule";
import { formatRoundOptionLabel } from "@/lib/admin/roundLabel";
import { formatDateTimeRu, fromDatetimeLocal, toDatetimeLocal } from "@/lib/admin/format";
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
import { AdminTh } from "@/components/ui/AdminTable";
import { Button } from "@/components/ui/Button";
import { Callout } from "@/components/ui/Callout";
import { DataTable } from "@/components/ui/DataTable";
import { Select } from "@/components/ui/Select";
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
  const { user } = useAuth();
  const isAdmin = user?.role === "ADMIN";
  const selectedRound = rounds.find((r) => r.id === selectedRoundId) ?? null;
  const effectiveDeadlinePassed =
    deadlinePassed || (selectedRound != null && isDeadlinePassedNow(selectedRound.deadline));
  const hasDraft = rounds.some((r) => r.status === "DRAFT");
  const atRoundCap = rounds.length >= contest.total_rounds;

  const uiMode = deriveAdminUiMode({
    contest,
    round: selectedRound,
    matches,
    deadlinePassed: effectiveDeadlinePassed,
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
      : isDeadlinePlacementValid(deadlineIso, new Date(earliest).toISOString(), contest.rules_json);
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
    (deadlineDirty && (!deadlineValid || deadlineChangeBlocked || !uiMode.canEditDeadline));

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
  const effectiveStatus = selectedRound
    ? effectiveRoundStatus(selectedRound, effectiveDeadlinePassed)
    : null;
  const isPhaseRound = effectiveStatus ? isPhaseRoundStatus(effectiveStatus) : false;
  const phaseRound =
    selectedRound && effectiveStatus
      ? { ...selectedRound, status: effectiveStatus }
      : selectedRound;

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
        <Select
          label="Тур:"
          value={selectedRoundId ?? ""}
          onChange={(e) => onSelectRound(Number(e.target.value))}
        >
          <option value="">Выберите тур</option>
          {rounds.map((r) => (
            <option key={r.id} value={r.id}>
              {formatRoundOptionLabel(r)}
            </option>
          ))}
        </Select>

        {!uiMode.disableAllMutations && (
          <Button size="sm" disabled={createDisabled} title={createTooltip} onClick={() => setShowCreateForm((v) => !v)}>
            + Создать тур
          </Button>
        )}

        {!uiMode.disableAllMutations && !hasDraft && (
          <Button variant="link" onClick={() => setShowFreeTour(true)}>
            + Добавить свободный тур
          </Button>
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
                    {formatRoundOptionLabel(selectedRound)}
                  </h3>
                  {selectedRound.status === "PUBLISHED" && (
                    <span className="text-sm font-medium text-green-700 bg-green-50 px-2 py-1 rounded">
                      Применено
                    </span>
                  )}
                </div>
                <RoundPhasePanel contest={contest} round={phaseRound!} matches={localMatches} />
              </section>
            ) : (
              /* DRAFT and ACTIVE panels */
              <section className="border border-gray-200 rounded-lg p-4">
                <div className="flex flex-wrap justify-between items-center gap-2 mb-4">
                  <h3 className="font-semibold text-gray-900">
                    {formatRoundOptionLabel(selectedRound)}
                  </h3>
                  {/* DRAFT: Редактировать / Активировать */}
                  {selectedRound.status === "DRAFT" && !uiMode.disableAllMutations && (
                    <div className="flex gap-2">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => setShowDraftEdit((v) => !v)}
                      >
                        {showDraftEdit ? "Свернуть" : "Редактировать"}
                      </Button>
                      <Button variant="success" size="sm" onClick={() => setShowActivate(true)}>
                        Активировать
                      </Button>
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
                {effectiveStatus === "ACTIVE" && (
                  <Callout variant="info" className="mb-3">
                    Тур активен. Состав матчей изменить нельзя. До начала матча можно перенести
                    время; отмена — в любой момент. Перенос на другую неделю — статус «Перенесён» и
                    свободный тур.
                  </Callout>
                )}
                {uiMode.showDeadlinePassedHint && (
                  <Callout variant="warning" className="mb-3">
                    Дедлайн прогнозов прошёл. Прогнозы закрыты; ввод результатов — на вкладке
                    «Результаты».
                  </Callout>
                )}

                {/* Deadline editor (hidden in DRAFT inline edit — form has its own field) */}
                {(effectiveStatus === "DRAFT" || effectiveStatus === "ACTIVE") &&
                  !(effectiveStatus === "DRAFT" && showDraftEdit) && (
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
                {effectiveStatus !== "DRAFT" || !showDraftEdit ? (
                  <DataTable variant="admin">
                    <thead className="bg-gray-50">
                      <tr>
                        <AdminTh>Матч</AdminTh>
                        <AdminTh>Дата</AdminTh>
                        <AdminTh>Статус</AdminTh>
                      </tr>
                    </thead>
                    <tbody>
                      {localMatches.map((m) => (
                        <MatchEditorRow
                          key={m.id}
                          match={m}
                          roundStatus={effectiveStatus ?? selectedRound.status}
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
                  </DataTable>
                ) : null}

                {saveError && <Callout variant="error" className="mt-4">{saveError}</Callout>}

                {(effectiveStatus === "ACTIVE" || effectiveStatus === "DRAFT") &&
                  !uiMode.disableAllMutations &&
                  effectiveStatus !== "DRAFT" && (
                    <Button className="mt-4" disabled={saveDisabled} onClick={handleSaveActive}>
                      Сохранить изменения
                    </Button>
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
            deadlinePassed={effectiveDeadlinePassed}
          />
        </div>
      )}

      {/* Activate confirm */}
      <ConfirmDialog
        open={showActivate}
        title="Активировать тур?"
        message={
          contest.is_locked
            ? "После активации участники смогут делать прогнозы. Состав матчей изменить уже нельзя — только перенос времени до начала, отмена или перенос в свободный тур."
            : "После активации конкурс будет заблокирован: нельзя менять число команд, туров и состав участников. Участники смогут делать прогнозы после активации тура."
        }
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
