import { fromDatetimeLocal } from "@/lib/admin/format";

export interface MatchDateDraft {
  date_time: string;
}

/** Prefill datetime for a newly added match row. */
export function nextMatchDateTime(
  matches: MatchDateDraft[],
  deadlineLocal: string,
): string {
  for (let i = matches.length - 1; i >= 0; i -= 1) {
    const value = matches[i]?.date_time?.trim();
    if (value) return value;
  }
  if (deadlineLocal.trim()) {
    return fromDatetimeLocal(deadlineLocal);
  }
  return "";
}
