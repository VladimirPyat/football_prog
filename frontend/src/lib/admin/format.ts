const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const DEFAULT_TEAM_LOGO_URL =
  process.env.NEXT_PUBLIC_DEFAULT_TEAM_LOGO_URL ??
  `${API_BASE}/static/assets/default-team-logo.jpg`;

export function formatDateRu(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export function formatDateTimeRu(iso: string): string {
  return new Date(iso).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function toDatetimeLocal(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function fromDatetimeLocal(value: string): string {
  return new Date(value).toISOString();
}

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
    CLOSED: "Дедлайн прогнозов прошёл. Введите счета матчей и просмотрите прогнозы",
    CALCULATED:
      "Очки посчитаны. Проверьте таблицу и нажмите «Опубликовать»",
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
    const kickoff = Date.parse(dateTimeIso);
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
