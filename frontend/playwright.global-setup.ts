import fs from "fs";
import path from "path";
import type { FullConfig } from "@playwright/test";
import {
  API_BASE,
  parseRootEnv,
  SUPERVISOR_LOGIN,
  type E2EUserCredentials,
} from "./e2e/fixtures/credentials";

const CREDENTIALS_PATH = path.resolve(__dirname, "e2e/.auth-credentials.json");

async function apiLogin(login: string, password: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ login, password }),
  });
  if (!res.ok) {
    throw new Error(`Login failed for ${login}: ${res.status} ${await res.text()}`);
  }
  return ((await res.json()) as { access_token: string }).access_token;
}

async function completeSetupViaToken(setupUrl: string, newPassword: string): Promise<void> {
  const token = new URL(setupUrl).searchParams.get("token");
  if (!token) {
    throw new Error(`setup_url missing token: ${setupUrl}`);
  }
  const res = await fetch(`${API_BASE}/api/v1/auth/complete-setup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, new_password: newPassword }),
  });
  if (!res.ok) {
    throw new Error(`complete-setup failed: ${res.status} ${await res.text()}`);
  }
}

async function provisionRegularUser(supervisorPassword: string): Promise<E2EUserCredentials> {
  const supervisorToken = await apiLogin(SUPERVISOR_LOGIN, supervisorPassword);
  const auth = { Authorization: `Bearer ${supervisorToken}` };

  const contestRes = await fetch(`${API_BASE}/api/v1/contests`, {
    method: "POST",
    headers: { ...auth, "Content-Type": "application/json" },
    body: JSON.stringify({ name: `E2E User Contest ${Date.now()}` }),
  });
  if (!contestRes.ok) {
    throw new Error(`Contest create failed: ${contestRes.status} ${await contestRes.text()}`);
  }
  const contestId = ((await contestRes.json()) as { id: number }).id;

  const login = `e2e_user_${Date.now()}`;
  const inviteRes = await fetch(`${API_BASE}/api/v1/contests/${contestId}/participants`, {
    method: "POST",
    headers: { ...auth, "Content-Type": "application/json" },
    body: JSON.stringify({
      email: `${login}@example.com`,
      first_name: "E2E",
      last_name: "User",
      login,
    }),
  });
  if (!inviteRes.ok) {
    throw new Error(`Invite failed: ${inviteRes.status} ${await inviteRes.text()}`);
  }
  const invite = (await inviteRes.json()) as {
    login: string;
    temp_password: string;
    setup_url: string;
  };

  const newPassword = "E2eUserPass1!";

  // ENFORCE_PASSWORD_SETUP=true (default): temp-password login returns 403 — use setup token.
  if (invite.setup_url) {
    await completeSetupViaToken(invite.setup_url, newPassword);
    return { login: invite.login, password: newPassword, contestId };
  }

  // Legacy path when enforce_password_setup=false
  const tempToken = await apiLogin(invite.login, invite.temp_password);
  const changeRes = await fetch(`${API_BASE}/api/v1/auth/change-password`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${tempToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      old_password: invite.temp_password,
      new_password: newPassword,
    }),
  });
  if (!changeRes.ok) {
    throw new Error(`Change password failed: ${changeRes.status} ${await changeRes.text()}`);
  }

  return { login: invite.login, password: newPassword, contestId };
}

export default async function globalSetup(_config: FullConfig): Promise<void> {
  console.log("[E2E globalSetup] Checking API at", API_BASE);
  const health = await fetch(`${API_BASE}/health`).catch(() => null);
  if (!health?.ok) {
    throw new Error(
      `API not reachable at ${API_BASE}/health — start backend first:\n` +
        "  uv run uvicorn main:app --host 127.0.0.1 --port 8000\n" +
        "  (Playwright starts UI on :3000 automatically via webServer)",
    );
  }
  console.log("[E2E globalSetup] API OK — provisioning test user…");

  const rootEnv = parseRootEnv();
  const supervisorPassword = rootEnv.SEED_SUPERVISOR_PASSWORD ?? "";
  if (!supervisorPassword) {
    throw new Error(
      "SEED_SUPERVISOR_PASSWORD missing in root .env — required for E2E user provisioning",
    );
  }

  const credentials = await provisionRegularUser(supervisorPassword);
  fs.writeFileSync(CREDENTIALS_PATH, JSON.stringify(credentials, null, 2), "utf8");
  console.log("[E2E globalSetup] Done — user", credentials.login, "contest", credentials.contestId);
}
