import { UNAUTHORIZED_EVENT } from "@/lib/auth/token";
import { parseErrorDetail } from "@/lib/api/errors";
import { getToken } from "@/lib/auth/token";

export class AppError extends Error {
  constructor(
    public status: number,
    public detail: string,
    public code?: string,
  ) {
    super(detail);
    this.name = "AppError";
  }
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit & { auth?: boolean },
): Promise<T> {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const headers = new Headers(options?.headers);
  const isFormData = typeof FormData !== "undefined" && options?.body instanceof FormData;
  if (!headers.has("Content-Type") && !isFormData) {
    headers.set("Content-Type", "application/json");
  }

  if (options?.auth !== false) {
    const token = getToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(`${base}${path}`, { ...options, headers });

  if (res.status === 401) {
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
    }
    throw new AppError(401, "Unauthorized");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const { detail, code } = parseErrorDetail(body);
    throw new AppError(res.status, detail, code);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export function apiGet<T>(path: string, auth = true): Promise<T> {
  return apiFetch<T>(path, { method: "GET", auth });
}

export function apiPost<T>(path: string, body: unknown, auth = true): Promise<T> {
  return apiFetch<T>(path, {
    method: "POST",
    body: JSON.stringify(body),
    auth,
  });
}

export function apiPatch<T>(path: string, body: unknown, auth = true): Promise<T> {
  return apiFetch<T>(path, {
    method: "PATCH",
    body: JSON.stringify(body),
    auth,
  });
}

export function apiPut<T>(path: string, body: unknown, auth = true): Promise<T> {
  return apiFetch<T>(path, {
    method: "PUT",
    body: JSON.stringify(body),
    auth,
  });
}

export function apiDelete<T>(path: string, body?: unknown, auth = true): Promise<T> {
  return apiFetch<T>(path, {
    method: "DELETE",
    body: body !== undefined ? JSON.stringify(body) : undefined,
    auth,
  });
}

export async function apiUpload<T>(path: string, file: File, fieldName = "file"): Promise<T> {
  const fd = new FormData();
  fd.append(fieldName, file);
  return apiFetch<T>(path, { method: "POST", body: fd });
}
