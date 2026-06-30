import type { PredictionEntryOut } from "@/types/api";

/** Display names of bootstrap staff users who are not prediction participants. */
const STAFF_MATRIX_NAMES = new Set(
  ["admin user", "supervisor user", "admin", "supervisor"].map((s) => s.toLowerCase()),
);

/** Remove staff accounts (e.g. Admin User) from public prediction matrices. */
export function filterParticipantEntries(entries: PredictionEntryOut[]): PredictionEntryOut[] {
  return entries.filter((entry) => {
    const name = (entry.user_name ?? "").trim().toLowerCase();
    return name.length > 0 && !STAFF_MATRIX_NAMES.has(name);
  });
}
