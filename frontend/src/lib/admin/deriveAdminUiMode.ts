import type { ContestOut, RoundOut } from "@/types/api";
import { canChangeDeadline, getDeadlineRuleHours } from "@/lib/admin/deadlineRule";

export interface AdminUiMode {
  /** Settings pages only — contest is locked for structural edits. */
  showSetupLockBanner: boolean;
  /** @deprecated use showSetupLockBanner; kept for backward compat */
  showLockBanner: boolean;
  showPausedBanner: boolean;
  showFinishedBanner: boolean;
  setupReadonly: boolean;
  disableAllMutations: boolean;
  canCreateRound: boolean;
  canEditRoundStructure: boolean;
  canEditMatchStatusAndDate: boolean;
  canEditDeadline: boolean;
  /** Whether the deadline change window is open (ACTIVE rounds only). */
  canChangeDeadline: boolean;
  roundEditorReadonly: boolean;
  showActiveRoundHint: boolean;
  showDeadlinePassedHint: boolean;
  canEnterResults: boolean;
  canCalculate: boolean;
  canPublish: boolean;
  resultsReadonly: boolean;
  canVoidMatch: boolean;
  showAppliedBadge: boolean;
}

interface DeriveAdminUiModeInput {
  contest: ContestOut | null;
  round: RoundOut | null;
  matches?: { date_time: string; status?: string }[];
  deadlinePassed?: boolean;
  /** True when any round in contest is DRAFT (for create-round form visibility). */
  hasDraftRound?: boolean;
  /** Current wall-clock time; defaults to Date.now() if omitted. */
  now?: Date;
}

export function deriveAdminUiMode({
  contest,
  round,
  deadlinePassed = false,
  hasDraftRound = false,
  now = new Date(),
}: DeriveAdminUiModeInput): AdminUiMode {
  const isLocked = contest?.is_locked ?? false;
  const status = contest?.status ?? null;
  const isPaused = status === "PAUSED";
  const isFinished = status === "FINISHED";
  const roundStatus = round?.status ?? null;

  const showSetupLockBanner = isLocked;
  const showLockBanner = showSetupLockBanner; // backward compat alias
  const showPausedBanner = isPaused;
  const showFinishedBanner = isFinished;
  const disableAllMutations = isPaused || isFinished;
  const setupReadonly = isLocked || disableAllMutations;

  const canCreateRound = !disableAllMutations && !hasDraftRound;

  const isActiveRound = roundStatus === "ACTIVE";

  // F3: structure editable in DRAFT, or in ACTIVE before deadline
  const beforePredictionDeadline = isActiveRound && !deadlinePassed;
  const canEditRoundStructure =
    !disableAllMutations && (roundStatus === "DRAFT" || beforePredictionDeadline);

  // F3: status + date editable in DRAFT or ACTIVE (including after deadline)
  const canEditMatchStatusAndDate =
    !disableAllMutations && (roundStatus === "DRAFT" || isActiveRound);

  // F2: canChangeDeadline = ACTIVE + change window open
  const ruleHours = getDeadlineRuleHours(contest?.rules_json ?? {});
  const changeWindowOpen =
    isActiveRound &&
    !deadlinePassed &&
    round?.deadline != null &&
    canChangeDeadline(now, round.deadline, ruleHours);

  const canEditDeadline =
    !disableAllMutations &&
    (roundStatus === "DRAFT" || (isActiveRound && !deadlinePassed && changeWindowOpen));

  const roundEditorReadonly =
    roundStatus === "CLOSED" ||
    roundStatus === "CALCULATED" ||
    roundStatus === "PUBLISHED" ||
    disableAllMutations;

  const showActiveRoundHint = isActiveRound;
  const showDeadlinePassedHint = isActiveRound && deadlinePassed;

  const canEnterResults = roundStatus === "CLOSED" && !disableAllMutations;
  const canCalculate = roundStatus === "CLOSED" && !disableAllMutations;
  const canPublish = roundStatus === "CALCULATED" && !disableAllMutations;
  const resultsReadonly =
    roundStatus === "CALCULATED" || roundStatus === "PUBLISHED" || disableAllMutations;
  const canVoidMatch =
    (roundStatus === "CLOSED" || roundStatus === "CALCULATED" || roundStatus === "PUBLISHED") &&
    !disableAllMutations;
  const showAppliedBadge = roundStatus === "PUBLISHED";

  return {
    showSetupLockBanner,
    showLockBanner,
    showPausedBanner,
    showFinishedBanner,
    setupReadonly,
    disableAllMutations,
    canCreateRound,
    canEditRoundStructure,
    canEditMatchStatusAndDate,
    canEditDeadline,
    canChangeDeadline: changeWindowOpen,
    roundEditorReadonly,
    showActiveRoundHint,
    showDeadlinePassedHint,
    canEnterResults,
    canCalculate,
    canPublish,
    resultsReadonly,
    canVoidMatch,
    showAppliedBadge,
  };
}
