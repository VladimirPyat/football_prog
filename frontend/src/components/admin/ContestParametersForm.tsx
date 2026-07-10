"use client";

import { useEffect, useState, type FormEvent } from "react";
import {
  contestParametersSchema,
  deriveRoundRobinStructure,
  isRoundRobinTeamCountValid,
  ROUND_ROBIN_ODD_TEAMS_MSG,
} from "@/lib/validation/admin";
import type { ZodIssue } from "zod";
import type { ContestOut } from "@/types/api";
import { RulesEditorPanel } from "@/components/admin/RulesEditorPanel";
import { ContestLifecycleActions } from "@/components/admin/ContestLifecycleActions";
import { ContestStartReadinessPanel } from "@/components/admin/ContestStartReadinessPanel";
import {
  buildRulesJsonPatch,
  rulesJsonToFormState,
  type RulesFormState,
} from "@/lib/admin/rulesEditor";
import { useContestStartReadiness } from "@/hooks/useContestStartReadiness";
import { Button } from "@/components/ui/Button";

const SETUP_HINT_KEY = (id: number) => `contest_setup_hint_${id}`;

interface ContestParametersFormProps {
  contest: ContestOut;
  readonly: boolean;
  onSave: (data: {
    total_teams: number;
    matches_per_round: number;
    total_rounds: number;
    is_round_robin: boolean;
    rules_json: Record<string, unknown>;
  }) => Promise<void>;
  onLifecycleSuccess: (action: "pause" | "resume" | "start" | "delete") => Promise<void>;
  onLifecycleError: (message: string) => void;
  onValidationError: (message: string) => void;
}

export function ContestParametersForm({
  contest,
  readonly,
  onSave,
  onLifecycleSuccess,
  onLifecycleError,
  onValidationError,
}: ContestParametersFormProps) {
  const [totalTeams, setTotalTeams] = useState(contest.total_teams);
  const [matchesPerRound, setMatchesPerRound] = useState(contest.matches_per_round);
  const [totalRounds, setTotalRounds] = useState(contest.total_rounds);
  const [isRoundRobin, setIsRoundRobin] = useState(contest.is_round_robin);
  const [rulesForm, setRulesForm] = useState<RulesFormState>(() =>
    rulesJsonToFormState(contest.rules_json as Record<string, unknown>),
  );
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [showSetupHint, setShowSetupHint] = useState(false);
  const {
    readiness,
    loading: readinessLoading,
    refetch: refetchReadiness,
  } = useContestStartReadiness(contest.id, contest.total_teams);

  useEffect(() => {
    setTotalTeams(contest.total_teams);
    setMatchesPerRound(contest.matches_per_round);
    setTotalRounds(contest.total_rounds);
    setIsRoundRobin(contest.is_round_robin);
    setRulesForm(rulesJsonToFormState(contest.rules_json as Record<string, unknown>));
  }, [contest]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const key = SETUP_HINT_KEY(contest.id);
    if (sessionStorage.getItem(key) === "1") {
      setShowSetupHint(true);
      sessionStorage.removeItem(key);
    }
  }, [contest.id]);

  const derivedReadonly = readonly || isRoundRobin;
  const roundRobinStructureInvalid = isRoundRobin && !isRoundRobinTeamCountValid(totalTeams);

  const applyRoundRobinDerived = (teams: number) => {
    const derived = deriveRoundRobinStructure(teams);
    if (derived) {
      setMatchesPerRound(derived.matches_per_round);
      setTotalRounds(derived.total_rounds);
    }
  };

  const handleTotalTeamsChange = (value: number) => {
    setTotalTeams(value);
    if (isRoundRobin) {
      applyRoundRobinDerived(value);
    }
  };

  const handleArbitraryToggle = (checked: boolean) => {
    const nextRoundRobin = !checked;
    setIsRoundRobin(nextRoundRobin);
    if (nextRoundRobin) {
      applyRoundRobinDerived(totalTeams);
    }
  };

  const persistParameters = async (): Promise<boolean> => {
    if (readonly) return true;
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
      onValidationError("Проверьте параметры структуры");
      return false;
    }
    const rules_json = buildRulesJsonPatch(
      contest.rules_json as Record<string, unknown>,
      rulesForm,
      parsed.data,
    );
    await onSave({ ...parsed.data, rules_json });
    return true;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await persistParameters();
    } finally {
      setSubmitting(false);
    }
  };

  const handleBeforeStart = async (): Promise<boolean> => {
    const latest = await refetchReadiness();
    if (!latest.ready) {
      onLifecycleError(latest.issues.join(" "));
      return false;
    }
    setSubmitting(true);
    try {
      return await persistParameters();
    } finally {
      setSubmitting(false);
    }
  };

  const rulesView = readonly
    ? rulesJsonToFormState(contest.rules_json as Record<string, unknown>)
    : rulesForm;

  return (
    <>
      {showSetupHint && (
        <p className="text-sm text-gray-600 mb-4 max-w-2xl">
          Задайте число команд, туров и матчей в туре, затем добавьте команды и участников. Запуск
          конкурса — кнопка внизу страницы.
        </p>
      )}

      {readonly && contest.status === "DRAFT" && !contest.is_locked && (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 mb-4 max-w-2xl">
          <p>
            Режим только для чтения при неожиданном состоянии. Переключите конкурс в шапке (должен
            быть <strong>DRAFT</strong>, не RUNNING).
          </p>
        </div>
      )}

      {readonly && contest.status !== "DRAFT" && (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 mb-4 max-w-2xl">
          <p>
            Параметры структуры редактируются только на этапе «Настройка» (конкурс DRAFT, не
            запущен). Сейчас: <strong>{contest.status}</strong>. Создайте новый конкурс («+ Новый
            конкурс») или выберите черновик в списке (статус DRAFT в скобках).
          </p>
        </div>
      )}

      {readonly && contest.status === "DRAFT" && contest.is_locked && (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 mb-4 max-w-2xl">
          <p>Выберите другой конкурс в шапке или создайте новый.</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6 pb-24">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-2xl">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Команд</label>
            <input
              type="number"
              value={totalTeams}
              onChange={(e) => handleTotalTeamsChange(Number(e.target.value))}
              disabled={readonly}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm disabled:bg-gray-100"
            />
            {errors.total_teams && <p className="text-sm text-red-600">{errors.total_teams}</p>}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Матчей в туре</label>
            <input
              type="number"
              value={roundRobinStructureInvalid ? "" : matchesPerRound}
              onChange={(e) => setMatchesPerRound(Number(e.target.value))}
              disabled={derivedReadonly}
              readOnly={isRoundRobin && !readonly}
              placeholder={roundRobinStructureInvalid ? "—" : undefined}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm disabled:bg-gray-100"
            />
            {roundRobinStructureInvalid && (
              <p className="text-sm text-amber-700 mt-1">{ROUND_ROBIN_ODD_TEAMS_MSG}</p>
            )}
            {errors.matches_per_round && (
              <p className="text-sm text-red-600">{errors.matches_per_round}</p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Туров</label>
            <input
              type="number"
              value={roundRobinStructureInvalid ? "" : totalRounds}
              onChange={(e) => setTotalRounds(Number(e.target.value))}
              disabled={derivedReadonly}
              readOnly={isRoundRobin && !readonly}
              placeholder={roundRobinStructureInvalid ? "—" : undefined}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm disabled:bg-gray-100"
            />
            {errors.total_rounds && <p className="text-sm text-red-600">{errors.total_rounds}</p>}
          </div>
          <div className="flex items-center gap-2 pt-6">
            <input
              id="round-robin"
              type="checkbox"
              checked={!isRoundRobin}
              onChange={(e) => handleArbitraryToggle(e.target.checked)}
              disabled={readonly}
            />
            <label htmlFor="round-robin" className="text-sm text-gray-700">
              Произвольное количество
            </label>
          </div>
        </div>

        <div className="text-sm text-gray-600 max-w-2xl space-y-1">
          <p>По умолчанию (галочка снята): круговая система — каждая пара играет дома и в гости.</p>
          <ul className="list-disc list-inside pl-1 space-y-0.5">
            <li>число команд должно быть чётным</li>
            <li>матчей в туре = число команд ÷ 2</li>
            <li>число туров = (число команд − 1) × 2</li>
          </ul>
          <p>
            Если нужен другой формат (кубок, неполный круг) — включите «Произвольное количество» и
            задайте значения вручную.
          </p>
        </div>

        {!readonly && contest.status === "DRAFT" && (
          <ContestStartReadinessPanel readiness={readiness} loading={readinessLoading} />
        )}

        <RulesEditorPanel
          form={rulesView}
          readonly={readonly}
          onChange={readonly ? () => undefined : setRulesForm}
        />

        {!readonly && (
          <Button type="submit" disabled={submitting}>
            Сохранить параметры
          </Button>
        )}
      </form>

      <ContestLifecycleActions
        contest={contest}
        onBeforeStart={handleBeforeStart}
        startBlocked={!readiness.ready}
        startBlockReason={readiness.issues.join(" ")}
        onSuccess={onLifecycleSuccess}
        onError={onLifecycleError}
      />
    </>
  );
}
