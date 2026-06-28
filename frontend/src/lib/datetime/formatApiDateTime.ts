import { getDateTimeLocale, getDisplayTimeZone } from "@/lib/datetime/config";
import { parseApiUtcDate } from "@/lib/datetime/parseApiUtc";
import { utcToWallDateTimeLocal, wallDateTimeLocalToUtc } from "@/lib/datetime/zonedWallTime";

export function formatDateRu(iso: string): string {
  const locale = getDateTimeLocale();
  const timeZone = getDisplayTimeZone();
  return parseApiUtcDate(iso).toLocaleDateString(locale, {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    ...(timeZone ? { timeZone } : {}),
  });
}

export function formatDateTimeRu(iso: string): string {
  const locale = getDateTimeLocale();
  const timeZone = getDisplayTimeZone();
  return parseApiUtcDate(iso).toLocaleString(locale, {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    ...(timeZone ? { timeZone } : {}),
  });
}

/** API UTC ISO → value for `<input type="datetime-local">`. */
export function toDatetimeLocal(iso: string): string {
  const ms = parseApiUtcDate(iso);
  if (Number.isNaN(ms.getTime())) return "";

  const displayTz = getDisplayTimeZone();
  if (displayTz) {
    return utcToWallDateTimeLocal(ms, displayTz);
  }

  const d = ms;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** datetime-local value → UTC ISO for API (`…Z`). */
export function fromDatetimeLocal(value: string): string {
  if (!value) return "";
  const displayTz = getDisplayTimeZone();
  if (displayTz) {
    return wallDateTimeLocalToUtc(value, displayTz).toISOString();
  }
  return new Date(value).toISOString();
}
