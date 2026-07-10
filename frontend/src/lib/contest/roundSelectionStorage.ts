export type RoundSelectionScope =
  | "contest-public"
  | "predict"
  | "admin-rounds"
  | "admin-results";

const PREFIX = "fp_selected_round";

export function roundSelectionKey(contestId: number, scope: RoundSelectionScope): string {
  return `${PREFIX}:${contestId}:${scope}`;
}

export function getStoredRoundId(
  contestId: number,
  scope: RoundSelectionScope,
): number | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(roundSelectionKey(contestId, scope));
  if (!raw) return null;
  const id = Number(raw);
  return Number.isInteger(id) && id > 0 ? id : null;
}

export function setStoredRoundId(
  contestId: number,
  scope: RoundSelectionScope,
  roundId: number,
): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(roundSelectionKey(contestId, scope), String(roundId));
}

export function clearStoredRoundId(contestId: number, scope: RoundSelectionScope): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(roundSelectionKey(contestId, scope));
}

export function resolveRoundId(
  rounds: { id: number }[],
  storedId: number | null,
  pickDefault: () => number | null,
): number | null {
  if (rounds.length === 0) return null;
  if (storedId != null && rounds.some((r) => r.id === storedId)) {
    return storedId;
  }
  return pickDefault();
}
