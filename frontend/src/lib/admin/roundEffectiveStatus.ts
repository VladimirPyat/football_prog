import type { RoundOut, RoundStatus } from "@/types/api";
import { parseApiUtc } from "@/lib/datetime/parseApiUtc";

/** Client-side check — mirrors API `deadline_passed` (now >= deadline UTC). */
export function isDeadlinePassedNow(deadlineIso: string, now: Date = new Date()): boolean {
  const ms = parseApiUtc(deadlineIso);
  return !Number.isNaN(ms) && now.getTime() >= ms;
}

/** Display/status logic: ACTIVE + deadline passed → behave as CLOSED (Дедлайн). */
export function effectiveRoundStatus(
  round: Pick<RoundOut, "status" | "deadline">,
  deadlinePassed?: boolean,
): RoundStatus {
  const passed = deadlinePassed ?? isDeadlinePassedNow(round.deadline);
  if (round.status === "ACTIVE" && passed) return "CLOSED";
  return round.status;
}

export function isPhaseRoundStatus(status: RoundStatus): boolean {
  return status === "CLOSED" || status === "CALCULATED" || status === "PUBLISHED";
}
