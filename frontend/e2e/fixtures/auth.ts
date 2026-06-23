import type { Page } from "@playwright/test";
import { expect } from "@playwright/test";
import {
  API_BASE,
  SUPERVISOR_LOGIN,
  SUPERVISOR_PASSWORD,
  TOKEN_KEY,
  USER_LOGIN,
  USER_PASSWORD,
} from "./credentials";

export async function clearAuthStorage(page: Page): Promise<void> {
  await page.goto("/");
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
}

export async function openLoginModal(page: Page): Promise<void> {
  await page.goto("/");
  await page.getByRole("button", { name: "Вход" }).click();
  await page.getByRole("heading", { name: "Вход" }).waitFor();
}

export async function fillLoginForm(
  page: Page,
  login: string,
  password: string,
): Promise<void> {
  await page.getByLabel("Логин").fill(login);
  await page.getByLabel("Пароль").fill(password);
}

export async function submitLogin(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Войти" }).click();
}

export async function waitForAuthenticatedHeader(page: Page): Promise<void> {
  await expect(page.getByRole("link", { name: "Личный кабинет" })).toBeVisible({
    timeout: 10_000,
  });
  await expect(page.getByRole("button", { name: "Вход" })).not.toBeVisible();
}

export async function loginAsUser(page: Page): Promise<void> {
  await openLoginModal(page);
  await fillLoginForm(page, USER_LOGIN, USER_PASSWORD);
  await submitLogin(page);
  await waitForAuthenticatedHeader(page);
}

export async function loginAsSupervisor(page: Page): Promise<void> {
  if (!SUPERVISOR_PASSWORD) {
    throw new Error("SEED_SUPERVISOR_PASSWORD missing in root .env");
  }
  await openLoginModal(page);
  await fillLoginForm(page, SUPERVISOR_LOGIN, SUPERVISOR_PASSWORD);
  await submitLogin(page);
  await waitForAuthenticatedHeader(page);
}

export async function gotoProfile(page: Page): Promise<void> {
  await page.goto("/profile");
  await page.waitForURL(/\/profile/);
  await expect(page.getByRole("heading", { name: "Личный кабинет" })).toBeVisible();
}

export async function getApiToken(login: string, password: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ login, password }),
  });
  if (!res.ok) {
    throw new Error(`API login failed for ${login}: ${res.status} ${await res.text()}`);
  }
  const data = (await res.json()) as { access_token: string };
  return data.access_token;
}

export interface InvitedUser {
  login: string;
  tempPassword: string;
  contestId: number;
}

export async function inviteTempUser(): Promise<InvitedUser> {
  const supervisorToken = await getApiToken(SUPERVISOR_LOGIN, SUPERVISOR_PASSWORD);
  const suffix = Date.now();

  const contestRes = await fetch(`${API_BASE}/api/v1/contests`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${supervisorToken}`,
    },
    body: JSON.stringify({ name: `E2E Temp Contest ${suffix}` }),
  });
  if (!contestRes.ok) {
    throw new Error(`Contest create failed: ${contestRes.status} ${await contestRes.text()}`);
  }
  const contestId = ((await contestRes.json()) as { id: number }).id;

  const login = `e2e_temp_${suffix}`;
  const res = await fetch(`${API_BASE}/api/v1/contests/${contestId}/participants`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${supervisorToken}`,
    },
    body: JSON.stringify({
      email: `${login}@example.com`,
      first_name: "E2E",
      last_name: "Temp",
      login,
    }),
  });
  if (!res.ok) {
    throw new Error(`Invite failed: ${res.status} ${await res.text()}`);
  }
  const data = (await res.json()) as { login: string; temp_password: string };
  return { login: data.login, tempPassword: data.temp_password, contestId };
}

export function collectCorsConsoleFailures(page: Page): string[] {
  const failures: string[] = [];
  page.on("console", (msg) => {
    const text = msg.text();
    if (text.includes("CORS") || text.includes("Access-Control")) {
      failures.push(text);
    }
  });
  return failures;
}

export async function readToken(page: Page): Promise<string | null> {
  return page.evaluate((key) => localStorage.getItem(key), TOKEN_KEY);
}
