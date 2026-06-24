/** Client-side deadline validation mirroring backend round_service.set_deadline */

export function getDeadlineRuleHours(rules: Record<string, unknown>): number {
  const structure = rules.contest_structure as Record<string, unknown> | undefined;
  const hours = structure?.deadline_rule_hours;
  return typeof hours === "number" && hours > 0 ? hours : 24;
}

export function toTimestamp(value: string | Date): number {
  return typeof value === "string" ? Date.parse(value) : value.getTime();
}

export function isDeadlineValid(
  deadline: string | Date,
  earliestMatchDateTime: string | Date,
  ruleHours: number,
): boolean {
  const deadlineMs = toTimestamp(deadline);
  const earliestMs = toTimestamp(earliestMatchDateTime);
  if (Number.isNaN(deadlineMs) || Number.isNaN(earliestMs)) return false;
  return deadlineMs <= earliestMs - ruleHours * 3_600_000;
}

export function deadlineErrorMessage(ruleHours: number): string {
  return `Дедлайн должен быть не позже чем за ${ruleHours} ч до первого матча`;
}

export function earliestMatchTime(matches: { date_time: string }[]): number | null {
  if (!matches.length) return null;
  const times = matches.map((m) => Date.parse(m.date_time)).filter((t) => !Number.isNaN(t));
  if (!times.length) return null;
  return Math.min(...times);
}
