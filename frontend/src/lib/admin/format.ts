export const DEFAULT_TEAM_LOGO_URL =
  process.env.NEXT_PUBLIC_DEFAULT_TEAM_LOGO_URL ?? "/assets/default-team-logo.jpg";

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
    CLOSED: "Закрыт",
    CALCULATED: "Рассчитан",
    PUBLISHED: "Опубликован",
  };
  return map[status] ?? status;
}
