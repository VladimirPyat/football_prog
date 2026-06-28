import type { Page } from "@playwright/test";
import { expect } from "@playwright/test";
import { execSync } from "child_process";
import { loginAsAdmin, loginAsSupervisor } from "./auth";
import {
  ACTIVE_CONTEST_KEY,
  ADMIN_LOGIN,
  ADMIN_PASSWORD,
  API_BASE,
  SUPERVISOR_LOGIN,
  SUPERVISOR_PASSWORD,
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

export interface ParticipantInviteOut {
  user_id: number;
  login: string;
  temp_password: string;
  setup_url: string;
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

export async function adminToken(): Promise<string> {
  if (!ADMIN_PASSWORD) throw new Error("SEED_ADMIN_PASSWORD missing");
  return apiLogin(ADMIN_LOGIN, ADMIN_PASSWORD);
}

export async function createDraftContest(
  token: string,
  name: string,
  opts: {
    total_teams?: number;
    total_rounds?: number;
    matches_per_round?: number;
    is_round_robin?: boolean;
    slug?: string;
  } = {},
): Promise<ContestOut> {
  const body: Record<string, unknown> = { name };
  if (opts.slug) body.slug = opts.slug;
  if (opts.total_teams !== undefined) body.total_teams = opts.total_teams;
  if (opts.total_rounds !== undefined) body.total_rounds = opts.total_rounds;
  if (opts.matches_per_round !== undefined) body.matches_per_round = opts.matches_per_round;
  if (opts.is_round_robin !== undefined) body.is_round_robin = opts.is_round_robin;
  const res = await fetch(`${API_BASE}/api/v1/contests`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(body),
  });
  return apiJson<ContestOut>(res, "createDraftContest");
}

export async function startContest(token: string, contestId: number): Promise<ContestOut> {
  const res = await fetch(`${API_BASE}/api/v1/contests/${contestId}/start`, {
    method: "POST",
    headers: authHeaders(token),
    body: "{}",
  });
  await apiJson<{ status: string }>(res, "startContest");
  return getContest(token, contestId);
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

export async function inviteParticipant(
  token: string,
  contestId: number,
  email: string,
  login: string,
  firstName: string,
  lastName: string,
): Promise<ParticipantInviteOut> {
  const res = await fetch(`${API_BASE}/api/v1/contests/${contestId}/participants`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({
      email,
      first_name: firstName,
      last_name: lastName,
      login,
    }),
  });
  return apiJson<ParticipantInviteOut>(res, "inviteParticipant");
}

export async function completeParticipantSetup(
  setupUrl: string,
  newPassword = "NewSecure1!",
): Promise<void> {
  const token = new URL(setupUrl).searchParams.get("token");
  if (!token) throw new Error(`setup token missing in ${setupUrl}`);
  const res = await fetch(`${API_BASE}/api/v1/auth/complete-setup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, new_password: newPassword }),
  });
  if (!res.ok) throw new Error(`completeParticipantSetup: ${res.status} ${await res.text()}`);
}

export async function fulfillStartPrerequisites(
  token: string,
  contestId: number,
  opts: { skipTeams?: boolean } = {},
): Promise<void> {
  const contest = await getContest(token, contestId);
  if (!opts.skipTeams) {
    await addTeams(token, contestId, contest.total_teams);
  }
  const tag = `${contestId}_${Date.now()}`;
  for (let i = 0; i < 2; i += 1) {
    const invited = await inviteParticipant(
      token,
      contestId,
      `e2e_start_${tag}_${i}@example.com`,
      `e2e_start_${tag}_${i}`,
      "E2E",
      `Player${i + 1}`,
    );
    await completeParticipantSetup(invited.setup_url);
  }
}

export async function createDraftRound(
  token: string,
  contestId: number,
  body: {
    number: number;
    deadline: string;
    matches: { team1_id: number; team2_id: number; date_time: string }[];
  },
): Promise<{ round_id: number }> {
  const res = await fetch(`${API_BASE}/api/v1/contests/${contestId}/admin/rounds`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(body),
  });
  return apiJson<{ round_id: number }>(res, "createDraftRound");
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

export async function calculateRound(
  token: string,
  contestId: number,
  roundId: number,
): Promise<void> {
  const res = await fetch(
    `${API_BASE}/api/v1/contests/${contestId}/admin/rounds/${roundId}/calculate`,
    { method: "POST", headers: authHeaders(token), body: "{}" },
  );
  if (!res.ok) throw new Error(`calculateRound: ${res.status} ${await res.text()}`);
}

export async function publishRound(
  token: string,
  contestId: number,
  roundId: number,
): Promise<void> {
  const res = await fetch(
    `${API_BASE}/api/v1/contests/${contestId}/admin/rounds/${roundId}/publish`,
    { method: "POST", headers: authHeaders(token), body: "{}" },
  );
  if (!res.ok) throw new Error(`publishRound: ${res.status} ${await res.text()}`);
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
  const token = await adminToken();
  const contest = await getContest(token, contestId);
  if (contest.status === "PAUSED") {
    await resumeContest(token, contestId);
  }
  if (contest.status === "DRAFT") {
    ensureLoadedContestDevState();
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

export async function waitForAdminShell(page: Page): Promise<void> {
  await expect(page.getByRole("link", { name: "Настройки" })).toBeVisible({
    timeout: 20_000,
  });
}

export async function seedSupervisorSession(page: Page): Promise<void> {
  if (!SUPERVISOR_PASSWORD) throw new Error("SEED_SUPERVISOR_PASSWORD missing");
  await loginAsSupervisor(page);
}

export async function seedAdminSession(page: Page): Promise<void> {
  if (!ADMIN_PASSWORD) throw new Error("SEED_ADMIN_PASSWORD missing");
  await loginAsAdmin(page);
}

export function ensureLoadedContestDevState(): void {
  execSync(
    "cd /work/football_prog && uv run python src/scripts/dev_setup.py --ensure-running-only",
    { stdio: "pipe" },
  );
}

export function reloadLoadedContestFixture(): void {
  console.log("[E2E] reloadLoadedContestFixture — load_test_data --reset (may take 60–120s)…");
  execSync(
    "cd /work/football_prog && uv run python src/scripts/load_test_data.py --reset && " +
      "uv run python src/scripts/bootstrap_users.py && " +
      "uv run python src/scripts/dev_setup.py --ensure-running-only",
    { stdio: "inherit", timeout: 180_000 },
  );
  console.log("[E2E] reloadLoadedContestFixture — done");
}

const ROUND_STATUS_LABELS: Record<string, string> = {
  DRAFT: "Черновик",
  ACTIVE: "Активен",
  CLOSED: "Закрыт",
  CALCULATED: "Рассчитан",
  PUBLISHED: "Опубликован",
};

export function roundOptionLabel(roundNumber: number, status: string): string {
  return `Тур ${roundNumber} — ${ROUND_STATUS_LABELS[status] ?? status}`;
}

export async function ensureRound10Active(contestId = 1): Promise<RoundOut> {
  ensureLoadedContestDevState();
  let token = await supervisorToken();
  let rounds = await getRounds(token, contestId);
  let round10 = rounds.find((r) => r.number === 10);
  if (!round10 || round10.status !== "ACTIVE") {
    reloadLoadedContestFixture();
    token = await supervisorToken();
    rounds = await getRounds(token, contestId);
    round10 = rounds.find((r) => r.number === 10);
  }
  if (!round10 || round10.status !== "ACTIVE") {
    throw new Error(`Round 10 not ACTIVE after reload (status=${round10?.status ?? "missing"})`);
  }
  return round10;
}

export async function ensureRoundPublished(
  token: string,
  contestId: number,
  roundNumber: number,
): Promise<RoundOut> {
  let rounds = await getRounds(token, contestId);
  let round = rounds.find((r) => r.number === roundNumber);
  if (!round) throw new Error(`Round ${roundNumber} not found`);
  if (round.status === "PUBLISHED") return round;
  if (round.status === "CLOSED") {
    await calculateRound(token, contestId, round.id);
    rounds = await getRounds(token, contestId);
    round = rounds.find((r) => r.number === roundNumber)!;
  }
  if (round.status === "CALCULATED") {
    await publishRound(token, contestId, round.id);
    rounds = await getRounds(token, contestId);
    round = rounds.find((r) => r.number === roundNumber)!;
  }
  if (round.status !== "PUBLISHED") {
    throw new Error(`Round ${roundNumber} not PUBLISHED (status=${round.status})`);
  }
  return round;
}

/** Round selector on /admin/rounds and /admin/results (not the header contest picker). */
export async function selectRoundByLabel(page: Page, label: string): Promise<void> {
  const roundSelect = page.locator('label:text-is("Тур:") + select');
  await roundSelect.waitFor({ state: "visible", timeout: 15_000 });
  await roundSelect.selectOption({ label });
}

export async function selectRoundByNumber(
  page: Page,
  token: string,
  contestId: number,
  roundNumber: number,
): Promise<RoundOut> {
  const rounds = await getRounds(token, contestId);
  const round = rounds.find((r) => r.number === roundNumber);
  if (!round) throw new Error(`Round ${roundNumber} not found`);
  const roundSelect = page.locator('label:text-is("Тур:") + select');
  await roundSelect.waitFor({ state: "visible", timeout: 15_000 });
  await roundSelect.selectOption(String(round.id));
  return round;
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

export async function setMatchResult(
  token: string,
  contestId: number,
  matchId: number,
  score1: number,
  score2: number,
): Promise<void> {
  const res = await fetch(
    `${API_BASE}/api/v1/contests/${contestId}/admin/matches/${matchId}/result`,
    {
      method: "PUT",
      headers: authHeaders(token),
      body: JSON.stringify({ score1, score2 }),
    },
  );
  if (!res.ok) throw new Error(`setMatchResult: ${res.status} ${await res.text()}`);
}

export function finalizeLoadedContestFixture(): void {
  console.log("[E2E] finalizeLoadedContestFixture…");
  execSync(
    "cd /work/football_prog && uv run python src/scripts/dev_setup.py --finalize-fixture-only",
    { stdio: "inherit", timeout: 180_000 },
  );
  console.log("[E2E] finalizeLoadedContestFixture — done");
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
