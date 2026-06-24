import fs from "fs";
import path from "path";

const ROOT_ENV = path.resolve(__dirname, "../../../.env");
const CREDENTIALS_PATH = path.resolve(__dirname, "../.auth-credentials.json");

export interface E2EUserCredentials {
  login: string;
  password: string;
  contestId: number;
}

export function parseRootEnv(): Record<string, string> {
  if (!fs.existsSync(ROOT_ENV)) return {};
  const out: Record<string, string> = {};
  for (const line of fs.readFileSync(ROOT_ENV, "utf8").split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq === -1) continue;
    const key = trimmed.slice(0, eq).trim();
    let value = trimmed.slice(eq + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    out[key] = value;
  }
  return out;
}

const rootEnv = parseRootEnv();

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export const SUPERVISOR_LOGIN = rootEnv.SEED_SUPERVISOR_LOGIN ?? "supervisor";
export const SUPERVISOR_PASSWORD =
  process.env.E2E_SUPERVISOR_PASSWORD ?? rootEnv.SEED_SUPERVISOR_PASSWORD ?? "";

export const ADMIN_LOGIN = rootEnv.SEED_ADMIN_LOGIN ?? "admin";
export const ADMIN_PASSWORD =
  process.env.E2E_ADMIN_PASSWORD ?? rootEnv.SEED_ADMIN_PASSWORD ?? "";

/** Bootstrap demo user from `bootstrap_users.py` (Stage 2.1.1). */
export const DEMO_USER_LOGIN = "user";
export const DEMO_USER_PASSWORD = "user";

export const TOKEN_KEY = "fp_access_token";
export const ACTIVE_CONTEST_KEY = "fp_active_contest_id";

function loadProvisionedUser(): E2EUserCredentials | null {
  if (!fs.existsSync(CREDENTIALS_PATH)) return null;
  try {
    return JSON.parse(fs.readFileSync(CREDENTIALS_PATH, "utf8")) as E2EUserCredentials;
  } catch {
    return null;
  }
}

const provisioned = loadProvisionedUser();

/** Documented dev login `user/user` is unavailable after loader (placeholder hash). */
export const USER_LOGIN = provisioned?.login ?? "user";
export const USER_PASSWORD = provisioned?.password ?? "user";
export const USER_CONTEST_ID = provisioned?.contestId ?? 1;

export const DOCUMENTED_USER_LOGIN_UNAVAILABLE =
  provisioned !== null || USER_LOGIN !== "user";
