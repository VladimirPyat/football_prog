import { parseApiUtc } from "@/lib/datetime/parseApiUtc";

/** Match schedule editing rules for supervisor ACTIVE rounds (frontend-only policy). */

export const LONG_POSTPONE_MS = 7 * 24 * 3_600_000;

export function matchKickoffMs(dateTime: string): number | null {
  const ms = parseApiUtc(dateTime);
  return Number.isNaN(ms) ? null : ms;
}

/** Reschedule kickoff time until the match has started (ignores prediction deadline). */
export function canRescheduleMatch(
  match: { date_time: string; status: string },
  now: Date = new Date(),
): boolean {
  if (match.status === "CANCELED" || match.status === "FINISHED" || match.status === "VOID") {
    return false;
  }
  const kickoff = matchKickoffMs(match.date_time);
  return kickoff !== null && kickoff > now.getTime();
}

/** Cancel is allowed at any time while the match is not already terminal. */
export function canCancelMatch(match: { status: string }): boolean {
  return match.status !== "CANCELED" && match.status !== "FINISHED" && match.status !== "VOID";
}

/** Only ADMIN may restore CANCELED / POSTPONED back to SCHEDULED. */
export function canRestoreMatchStatus(match: { status: string }, isAdmin: boolean): boolean {
  return isAdmin && (match.status === "CANCELED" || match.status === "POSTPONED");
}

/** Mark POSTPONED for free-tour flow (league postponement outside the round window). */
export function canMarkPostponed(match: { status: string }): boolean {
  return match.status === "SCHEDULED";
}

export function isLongPostponement(
  originalDateTime: string,
  newDateTime: string,
  thresholdMs: number = LONG_POSTPONE_MS,
): boolean {
  const original = matchKickoffMs(originalDateTime);
  const next = matchKickoffMs(newDateTime);
  if (original === null || next === null) return false;
  return Math.abs(next - original) >= thresholdMs;
}

export function longPostponementHint(): string {
  return "Перенос более чем на неделю: отметьте матч как «Перенесён» и добавьте его в свободный тур.";
}
