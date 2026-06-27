/** Client-side deadline validation — mirrors updated backend round_service.set_deadline.
 *
 * Policy (2026-06-27):
 * - Placement: deadline must be in the future AND before first match.
 *   The 24h gap is no longer required between deadline and first match.
 * - Lockout: supervisor may change deadline only while
 *   now <= currentDeadline - ruleHours (24h window).
 */

export function getDeadlineRuleHours(rules: Record<string, unknown>): number {
  const structure = rules.contest_structure as Record<string, unknown> | undefined;
  const hours = structure?.deadline_rule_hours;
  return typeof hours === "number" && hours > 0 ? hours : 24;
}

export function toTimestamp(value: string | Date): number {
  return typeof value === "string" ? Date.parse(value) : value.getTime();
}

/** Placement rule: deadline must be strictly before first match (no ruleHours gap). */
export function isDeadlineValid(
  deadline: string | Date,
  earliestMatchDateTime: string | Date,
): boolean {
  const deadlineMs = toTimestamp(deadline);
  const earliestMs = toTimestamp(earliestMatchDateTime);
  if (Number.isNaN(deadlineMs) || Number.isNaN(earliestMs)) return false;
  return deadlineMs < earliestMs;
}

/** Lockout rule: deadline may be changed only while now <= currentDeadline - ruleHours. */
export function canChangeDeadline(
  now: Date | string,
  currentDeadline: Date | string,
  ruleHours: number,
): boolean {
  const nowMs = toTimestamp(now);
  const cutoffMs = toTimestamp(currentDeadline) - ruleHours * 3_600_000;
  return nowMs <= cutoffMs;
}

export function deadlineErrorMessage(): string {
  return "Дедлайн должен быть раньше первого матча тура";
}

export function deadlineChangeClosedMessage(ruleHours: number): string {
  return `Изменить дедлайн можно не позже чем за ${ruleHours} ч до текущего дедлайна`;
}

export function earliestMatchTime(matches: { date_time: string }[]): number | null {
  if (!matches.length) return null;
  const times = matches.map((m) => Date.parse(m.date_time)).filter((t) => !Number.isNaN(t));
  if (!times.length) return null;
  return Math.min(...times);
}
