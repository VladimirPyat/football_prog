export const ERROR_CODES = {
  NOT_FOUND: "NOT_FOUND",
  VALIDATION_ERROR: "VALIDATION_ERROR",
  SCORE_OUT_OF_RANGE: "SCORE_OUT_OF_RANGE",
  CONTEST_RULE_VIOLATION: "CONTEST_RULE_VIOLATION",
  DEADLINE_PASSED: "DEADLINE_PASSED",
  CONTEST_NOT_RUNNING: "CONTEST_NOT_RUNNING",
  CONTEST_LOCKED: "CONTEST_LOCKED",
  GRACE_PERIOD_ACTIVE: "GRACE_PERIOD_ACTIVE",
  ILLEGAL_TRANSITION: "ILLEGAL_TRANSITION",
  CONTEST_NOT_PAUSED: "CONTEST_NOT_PAUSED",
  INTERNAL_ERROR: "INTERNAL_ERROR",
} as const;

export type ErrorCode = (typeof ERROR_CODES)[keyof typeof ERROR_CODES];

export function isContestLocked(code?: string): boolean {
  return code === ERROR_CODES.CONTEST_LOCKED;
}

export function isDeadlinePassed(code?: string): boolean {
  return code === ERROR_CODES.DEADLINE_PASSED;
}

export function parseErrorDetail(body: unknown): { detail: string; code?: string } {
  if (!body || typeof body !== "object") {
    return { detail: "Unknown error" };
  }
  const record = body as Record<string, unknown>;
  const detail = record.detail;
  const code = typeof record.code === "string" ? record.code : undefined;

  if (typeof detail === "string") {
    return { detail, code };
  }
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        return null;
      })
      .filter(Boolean);
    return { detail: messages.join("; ") || "Ошибка валидации", code };
  }
  return { detail: "Unknown error", code };
}
