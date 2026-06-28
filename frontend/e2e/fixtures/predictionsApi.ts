import { execSync } from "child_process";
import path from "path";
import { API_BASE } from "./credentials";
import { SUPERVISOR_LOGIN, SUPERVISOR_PASSWORD } from "./credentials";

const REPO_ROOT = path.resolve(__dirname, "../../..");

async function supervisorAuthHeaders(): Promise<Record<string, string>> {
  if (!SUPERVISOR_PASSWORD) return {};
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ login: SUPERVISOR_LOGIN, password: SUPERVISOR_PASSWORD }),
  });
  if (!res.ok) return {};
  const token = ((await res.json()) as { access_token: string }).access_token;
  return { Authorization: `Bearer ${token}` };
}

export async function getContestMaxScore(contestId = 1): Promise<number> {
  const headers = await supervisorAuthHeaders();
  const r = await fetch(`${API_BASE}/api/v1/contests/${contestId}`, { headers });
  if (!r.ok) throw new Error(`getContestMaxScore: ${r.status}`);
  const j = (await r.json()) as {
    rules_json: { constraints: { score_validation_range: number[] } };
  };
  return j.rules_json.constraints.score_validation_range[1];
}

export async function getRoundIdByNumber(
  contestId: number,
  number: number,
  token?: string,
): Promise<number | undefined> {
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  const r = await fetch(`${API_BASE}/api/v1/contests/${contestId}/rounds`, { headers });
  if (!r.ok) throw new Error(`getRoundIdByNumber: ${r.status}`);
  const rounds = (await r.json()) as { id: number; number: number }[];
  return rounds.find((x) => x.number === number)?.id;
}

export async function getActiveRoundId(contestId = 1): Promise<number | undefined> {
  const r = await fetch(`${API_BASE}/api/v1/contests/${contestId}/rounds`);
  if (!r.ok) throw new Error(`getActiveRoundId: ${r.status}`);
  const rounds = (await r.json()) as { id: number; status: string }[];
  return rounds.find((x) => x.status === "ACTIVE")?.id;
}

export async function getRoundPredictions(
  contestId: number,
  roundId: number,
  token: string,
): Promise<{ deadline_passed: boolean; entries: { user_id: number; predictions: unknown }[] }> {
  const r = await fetch(`${API_BASE}/api/v1/contests/${contestId}/rounds/${roundId}/predictions`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(`getRoundPredictions: ${r.status}`);
  return r.json() as Promise<{
    deadline_passed: boolean;
    entries: { user_id: number; predictions: unknown }[];
  }>;
}

export async function submitPredictionsViaApi(
  contestId: number,
  roundId: number,
  token: string,
  matchIds: number[],
  score1 = 1,
  score2 = 0,
): Promise<void> {
  const predictions = matchIds.map((match_id) => ({ match_id, score1, score2 }));
  const r = await fetch(`${API_BASE}/api/v1/contests/${contestId}/rounds/${roundId}/predictions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ predictions }),
  });
  if (!r.ok) throw new Error(`submitPredictionsViaApi: ${r.status} ${await r.text()}`);
}

export async function getRoundMatchIds(
  contestId: number,
  roundId: number,
  token: string,
): Promise<number[]> {
  const view = await getRoundPredictions(contestId, roundId, token);
  return view.entries.length > 0
    ? (
        (await fetch(`${API_BASE}/api/v1/contests/${contestId}/rounds/${roundId}/predictions`, {
          headers: { Authorization: `Bearer ${token}` },
        }).then((r) => r.json())) as { matches: { id: number }[] }
      ).matches.map((m) => m.id)
    : [];
}

export async function patchRoundDeadlinePast(
  contestId: number,
  roundId: number,
  supervisorToken: string,
): Promise<void> {
  const past = new Date(Date.now() - 60_000).toISOString();
  const r = await fetch(`${API_BASE}/api/v1/contests/${contestId}/admin/rounds/${roundId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${supervisorToken}`,
    },
    body: JSON.stringify({ deadline: past }),
  });
  if (!r.ok) throw new Error(`patchRoundDeadlinePast: ${r.status} ${await r.text()}`);
}

export async function patchRoundDeadlineFuture(
  contestId: number,
  roundId: number,
  supervisorToken: string,
  hoursFromNow: number,
): Promise<void> {
  const future = new Date(Date.now() + hoursFromNow * 3600_000).toISOString();
  const r = await fetch(`${API_BASE}/api/v1/contests/${contestId}/admin/rounds/${roundId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${supervisorToken}`,
    },
    body: JSON.stringify({ deadline: future }),
  });
  if (!r.ok) throw new Error(`patchRoundDeadlineFuture: ${r.status} ${await r.text()}`);
}

/** Restore ACTIVE round 10 with a future deadline (dev_setup — avoids 24h PATCH lockout). */
export async function ensureE2eActiveRound(contestId = 1): Promise<number | undefined> {
  execSync("uv run python src/scripts/dev_setup.py --ensure-running-only --e2e", {
    cwd: REPO_ROOT,
    stdio: "ignore",
  });
  return getActiveRoundId(contestId);
}

export async function inviteContestParticipant(
  contestId: number,
  supervisorToken: string,
): Promise<{ login: string; password: string }> {
  const suffix = Date.now();
  const login = `e2e_pred_${suffix}`;
  const res = await fetch(`${API_BASE}/api/v1/contests/${contestId}/participants`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${supervisorToken}`,
    },
    body: JSON.stringify({
      email: `${login}@example.com`,
      first_name: "E2E",
      last_name: "Viewer",
      login,
    }),
  });
  if (!res.ok) throw new Error(`inviteContestParticipant: ${res.status} ${await res.text()}`);
  const data = (await res.json()) as { setup_url: string };
  const token = new URL(data.setup_url).searchParams.get("token");
  if (!token) throw new Error("setup_url missing token");
  const password = "E2eViewer1!";
  const setupRes = await fetch(`${API_BASE}/api/v1/auth/complete-setup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, new_password: password }),
  });
  if (!setupRes.ok) {
    throw new Error(`complete-setup failed: ${setupRes.status} ${await setupRes.text()}`);
  }
  return { login, password };
}
