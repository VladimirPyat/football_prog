import type { ContestOut, RoundOut } from "@/types/api";

export interface AdminUiMode {
  showLockBanner: boolean;
  showPausedBanner: boolean;
  showFinishedBanner: boolean;
  setupReadonly: boolean;
  disableAllMutations: boolean;
  canCreateRound: boolean;
  canEditRoundStructure: boolean;
  canEditMatchStatusAndDate: boolean;
  canEditDeadline: boolean;
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
}

export function deriveAdminUiMode({
  contest,
  round,
  deadlinePassed = false,
}: DeriveAdminUiModeInput): AdminUiMode {
  const isLocked = contest?.is_locked ?? false;
  const status = contest?.status ?? null;
  const isPaused = status === "PAUSED";
  const isFinished = status === "FINISHED";
  const roundStatus = round?.status ?? null;

  const showLockBanner = isLocked;
  const showPausedBanner = isPaused;
  const showFinishedBanner = isFinished;
  const disableAllMutations = isPaused || isFinished;
  const setupReadonly = isLocked || disableAllMutations;

  const canCreateRound = !disableAllMutations && roundStatus !== "DRAFT";
  const canEditRoundStructure = roundStatus === "DRAFT" && !disableAllMutations;

  const isActiveRound = roundStatus === "ACTIVE";
  const canEditMatchStatusAndDate = isActiveRound && !disableAllMutations;

  const canEditDeadline =
    (roundStatus === "DRAFT" || (isActiveRound && !deadlinePassed)) && !disableAllMutations;

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
    showLockBanner,
    showPausedBanner,
    showFinishedBanner,
    setupReadonly,
    disableAllMutations,
    canCreateRound,
    canEditRoundStructure,
    canEditMatchStatusAndDate,
    canEditDeadline,
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
