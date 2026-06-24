import type { Page } from "@playwright/test";
import { execSync } from "child_process";
import {
  ACTIVE_CONTEST_KEY,
  ADMIN_LOGIN,
  ADMIN_PASSWORD,
  API_BASE,
  SUPERVISOR_LOGIN,
  SUPERVISOR_PASSWORD,
  TOKEN_KEY,
} from "./credentials";

function authHeaders(token: string, json = true): Record<string, string> {
  const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
  if (json) headers["Content-Type"] = "application/json";
  return headers;
}

async function apiJson<T>(res: Response, context: string): Promise<T> {
  if (!res.ok) {
    throw new Error(`${context}: ${res.status} ${await res.text()}`);
  }
  return (await res.json()) as T;
}

export interface ContestOut {
  id: number;
  name: string;
  status: string;
  is_locked: boolean;
  total_teams: number;
  matches_per_round: number;
  total_rounds: number;
  is_round_robin: boolean;
  rules_json: Record<string, unknown>;
}

export interface TeamOut {
  id: number;
  name: string;
  short_name: string;
  logo_url: string | null;
}

export interface RoundOut {
  id: number;
  number: number;
  status: string;
  deadline: string;
}

export interface MatchOut {
  id: number;
  team1: string;
  team2: string;
  date_time: string;
  status: string;
  score1: number | null;
  score2: number | null;
}

export interface LeaderboardRow {
  user_id: number;
  user_name: string;
  total_with_bonus3: number;
}

export async function apiLogin(login: string, password: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ login, password }),
  });
  return (await apiJson<{ access_token: string }>(res, `login ${login}`)).access_token;
}

export async function supervisorToken(): Promise<string> {
  if (!SUPERVISOR_PASSWORD) throw new Error("SEED_SUPERVISOR_PASSWORD missing");
  return apiLogin(SUPERVISOR_LOGIN, SUPERVISOR_PASSWORD);
}

export async function createDraftContest(
  token: string,
  name: string,
  opts: {
    total_teams?: number;
    total_rounds?: number;
    matches_per_round?: number;
    is_round_robin?: boolean;
  } = {},
): Promise<ContestOut> {
  const res = await fetch(`${API_BASE}/api/v1/contests`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({
      name,
      total_teams: opts.total_teams ?? 4,
      total_rounds: opts.total_rounds ?? 2,
      matches_per_round: opts.matches_per_round ?? 2,
      is_round_robin: opts.is_round_robin ?? false,
    }),
  });
  return apiJson<ContestOut>(res, "createDraftContest");
}

export async function getContest(token: string, contestId: number): Promise<ContestOut> {
  const res = await fetch(`${API_BASE}/api/v1/contests/${contestId}`, {
    headers: authHeaders(token),
  });
  return apiJson<ContestOut>(res, "getContest");
}

export async function addTeam(
  token: string,
  contestId: number,
  name: string,
  shortName: string,
): Promise<TeamOut> {
  const res = await fetch(`${API_BASE}/api/v1/contests/${contestId}/teams`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({ name, short_name: shortName }),
  });
  return apiJson<TeamOut>(res, "addTeam");
}

export async function addTeams(
  token: string,
  contestId: number,
  count: number,
): Promise<TeamOut[]> {
  const tag = Math.random().toString(36).slice(2, 6);
  const teams: TeamOut[] = [];
  for (let i = 1; i <= count; i += 1) {
    teams.push(
      await addTeam(
        token,
        contestId,
        `E2E ${tag} Team ${i}`,
        `${tag.charAt(0)}${i}`.slice(0, 4).toUpperCase(),
      ),
    );
  }
  return teams;
}

export async function createDraftRound(
  token: string,
  contestId: number,
  body: {
    number: number;
    deadline: string;
    matches: { team1_id: number; team2_id: number; date_time: string }[];
  },
): Promise<{ id: number }> {
  const res = await fetch(`${API_BASE}/api/v1/contests/${contestId}/admin/rounds`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(body),
  });
  return apiJson<{ id: number }>(res, "createDraftRound");
}

export async function activateRound(
  token: string,
  contestId: number,
  roundId: number,
): Promise<void> {
  const res = await fetch(
    `${API_BASE}/api/v1/contests/${contestId}/admin/rounds/${roundId}/activate`,
    { method: "POST", headers: authHeaders(token), body: "{}" },
  );
  if (!res.ok) throw new Error(`activateRound: ${res.status} ${await res.text()}`);
}

export async function patchRound(
  token: string,
  contestId: number,
  roundId: number,
  body: {
    deadline?: string;
    matches?: { match_id: number; date_time?: string; status?: string }[];
  },
): Promise<void> {
  const res = await fetch(
    `${API_BASE}/api/v1/contests/${contestId}/admin/rounds/${roundId}`,
    { method: "PATCH", headers: authHeaders(token), body: JSON.stringify(body) },
  );
  if (!res.ok) throw new Error(`patchRound: ${res.status} ${await res.text()}`);
}

export async function closeRound(
  token: string,
  contestId: number,
  roundId: number,
): Promise<void> {
  const res = await fetch(
    `${API_BASE}/api/v1/contests/${contestId}/admin/rounds/${roundId}/close`,
    { method: "POST", headers: authHeaders(token), body: "{}" },
  );
  if (!res.ok) throw new Error(`closeRound: ${res.status} ${await res.text()}`);
}

export async function getRounds(token: string, contestId: number): Promise<RoundOut[]> {
  const res = await fetch(`${API_BASE}/api/v1/contests/${contestId}/rounds`, {
    headers: authHeaders(token),
  });
  return apiJson<RoundOut[]>(res, "getRounds");
}

export async function getRoundMatches(
  token: string,
  contestId: number,
  roundId: number,
): Promise<MatchOut[]> {
  const res = await fetch(
    `${API_BASE}/api/v1/contests/${contestId}/rounds/${roundId}/predictions`,
    { headers: authHeaders(token) },
  );
  const data = await apiJson<{ matches: MatchOut[] }>(res, "getRoundMatches");
  return data.matches;
}

export async function pauseContest(token: string, contestId: number): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/contests/${contestId}/pause`, {
    method: "POST",
    headers: authHeaders(token),
    body: "{}",
  });
  if (!res.ok) throw new Error(`pauseContest: ${res.status} ${await res.text()}`);
}

export async function resumeContest(token: string, contestId: number): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/contests/${contestId}/resume`, {
    method: "POST",
    headers: authHeaders(token),
    body: "{}",
  });
  if (!res.ok) throw new Error(`resumeContest: ${res.status} ${await res.text()}`);
}

export async function ensureContestRunning(contestId = 1): Promise<void> {
  const token = await supervisorToken();
  const contest = await getContest(token, contestId);
  if (contest.status === "PAUSED") {
    await resumeContest(token, contestId);
  }
}

export async function getLeaderboard(
  token: string,
  contestId: number,
): Promise<LeaderboardRow[]> {
  const res = await fetch(`${API_BASE}/api/v1/contests/${contestId}/leaderboard`, {
    headers: authHeaders(token),
  });
  const data = await apiJson<{ leaderboard: LeaderboardRow[] }>(res, "getLeaderboard");
  return data.leaderboard;
}

export async function getPublicResults(
  token: string,
  contestId: number,
  roundId: number,
): Promise<unknown> {
  const res = await fetch(
    `${API_BASE}/api/v1/contests/${contestId}/rounds/${roundId}/results`,
    { headers: authHeaders(token) },
  );
  return apiJson(res, "getPublicResults");
}

export function toDatetimeLocal(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function addHours(base: Date, hours: number): Date {
  return new Date(base.getTime() + hours * 3_600_000);
}

export function addDays(base: Date, days: number): Date {
  return addHours(base, days * 24);
}

export async function setActiveContest(page: Page, contestId: number): Promise<void> {
  await page.evaluate(
    ({ key, id }) => {
      localStorage.setItem(key, String(id));
    },
    { key: ACTIVE_CONTEST_KEY, id: contestId },
  );
}

export async function gotoAdminContest(
  page: Page,
  contestId: number,
  path: string,
): Promise<void> {
  await setActiveContest(page, contestId);
  await page.goto(path);
  await page.waitForLoadState("networkidle");
}

export async function seedStaffSession(
  page: Page,
  login: string,
  password: string,
): Promise<void> {
  const token = await apiLogin(login, password);
  await page.goto("/");
  await page.evaluate(
    ({ key, value }) => {
      localStorage.setItem(key, value);
    },
    { key: TOKEN_KEY, value: token },
  );
  await page.reload();
}

export async function seedSupervisorSession(page: Page): Promise<void> {
  if (!SUPERVISOR_PASSWORD) throw new Error("SEED_SUPERVISOR_PASSWORD missing");
  await seedStaffSession(page, SUPERVISOR_LOGIN, SUPERVISOR_PASSWORD);
}

export async function seedAdminSession(page: Page): Promise<void> {
  if (!ADMIN_PASSWORD) throw new Error("SEED_ADMIN_PASSWORD missing");
  await seedStaffSession(page, ADMIN_LOGIN, ADMIN_PASSWORD);
}

export function ensureLoadedContestDevState(): void {
  execSync(
    "cd /work/football_prog && uv run python src/scripts/dev_setup.py --ensure-running-only",
    { stdio: "pipe" },
  );
}

export async function ensureRound10Active(): Promise<void> {
  ensureLoadedContestDevState();
}

export async function selectContestInPicker(page: Page, contestName: string): Promise<void> {
  const picker = page.locator("header").getByLabel("Выбор конкурса");
  await picker.waitFor();
  const options = picker.locator("option");
  const count = await options.count();
  for (let i = 0; i < count; i += 1) {
    const text = (await options.nth(i).textContent()) ?? "";
    if (text.includes(contestName)) {
      const value = await options.nth(i).getAttribute("value");
      if (value) await picker.selectOption(value);
      return;
    }
  }
  throw new Error(`Contest not found in picker: ${contestName}`);
}

export async function moveRoundToPast(
  token: string,
  contestId: number,
  roundId: number,
): Promise<void> {
  const matches = await getRoundMatches(token, contestId, roundId);
  const past = addDays(new Date(), -2).toISOString();
  const deadlinePast = addDays(new Date(), -3).toISOString();
  await patchRound(
    token,
    contestId,
    roundId,
    {
      deadline: deadlinePast,
      matches: matches.map((m) => ({ match_id: m.id, date_time: past })),
    },
  );
  await closeRound(token, contestId, roundId);
}
