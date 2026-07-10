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
export const SUPERVISOR_PASSWORD = rootEnv.SEED_SUPERVISOR_PASSWORD ?? "";

export const ADMIN_LOGIN = rootEnv.SEED_SUPPORT_LOGIN ?? "support";
export const ADMIN_PASSWORD = rootEnv.SEED_SUPPORT_PASSWORD ?? "";

export const CONTRACTED_E2E_USER_LOGIN = "shutov";
export const CONTRACTED_E2E_USER_PASSWORD = "user";

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

/** Contracted CSV user from `load_test_data.py` (password `user` in dev). */
export const USER_LOGIN = provisioned?.login ?? CONTRACTED_E2E_USER_LOGIN;
export const USER_PASSWORD = provisioned?.password ?? CONTRACTED_E2E_USER_PASSWORD;
export const USER_CONTEST_ID = provisioned?.contestId ?? 1;

export const DOCUMENTED_USER_LOGIN_UNAVAILABLE = provisioned !== null;
