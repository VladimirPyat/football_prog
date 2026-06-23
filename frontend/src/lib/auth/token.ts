export const TOKEN_KEY = "fp_access_token";
export const ACTIVE_CONTEST_KEY = "fp_active_contest_id";
export const UNAUTHORIZED_EVENT = "fp:unauthorized";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
}

export function getActiveContestId(): number | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(ACTIVE_CONTEST_KEY);
  if (!raw) return null;
  const id = Number(raw);
  return Number.isInteger(id) && id > 0 ? id : null;
}

export function setActiveContestId(id: number): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(ACTIVE_CONTEST_KEY, String(id));
}
