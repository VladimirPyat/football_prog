import {
  formatDateRu,
  formatDateTimeRu,
  fromDatetimeLocal,
  toDatetimeLocal,
} from "@/lib/datetime/formatApiDateTime";
import { parseApiUtc } from "@/lib/datetime/parseApiUtc";

export { formatDateRu, formatDateTimeRu, fromDatetimeLocal, toDatetimeLocal };

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const DEFAULT_TEAM_LOGO_URL =
  process.env.NEXT_PUBLIC_DEFAULT_TEAM_LOGO_URL ??
  `${API_BASE}/static/assets/default-team-logo.jpg`;

export function participantStatusLabel(status: "PENDING" | "ACCEPTED"): string {
  return status === "PENDING" ? "Ожидает" : "Принято";
}

export function roundStatusLabel(status: string): string {
  const map: Record<string, string> = {
    DRAFT: "Черновик",
    ACTIVE: "Активен",
    CLOSED: "Дедлайн",
    CALCULATED: "Рассчитан",
    PUBLISHED: "Опубликован",
  };
  return map[status] ?? status;
}

export function roundStatusHint(status: string): string {
  const map: Record<string, string> = {
    DRAFT: "Тур собран, прогнозы ещё не принимаются",
    ACTIVE: "Участники делают прогнозы до дедлайна",
    CLOSED:
      "Дедлайн прошёл. После начала матча внесите счёт на вкладке «Результаты», затем «Рассчитать».",
    CALCULATED:
      "Очки посчитаны. Проверьте таблицу участников и нажмите «Опубликовать» на вкладке «Результаты».",
    PUBLISHED: "Тур зафиксирован в общей таблице",
  };
  return map[status] ?? "";
}

/** Display-only label for match phase on CLOSED rounds. */
export function matchPhaseLabel(
  matchStatus: string,
  dateTimeIso: string,
  roundStatus: string,
): string {
  if (roundStatus !== "CLOSED") {
    return matchStatusLabel(matchStatus);
  }
  if (matchStatus === "FINISHED") return "Завершён";
  if (matchStatus === "SCHEDULED") {
    const kickoff = parseApiUtc(dateTimeIso);
    if (!Number.isNaN(kickoff) && kickoff <= Date.now()) return "Идёт";
    return "Запланирован";
  }
  return matchStatusLabel(matchStatus);
}

export function matchStatusLabel(status: string): string {
  const map: Record<string, string> = {
    SCHEDULED: "Запланирован",
    POSTPONED: "Перенесён",
    CANCELED: "Отменён",
    VOID: "Аннулирован",
    FINISHED: "Завершён",
  };
  return map[status] ?? status;
}
