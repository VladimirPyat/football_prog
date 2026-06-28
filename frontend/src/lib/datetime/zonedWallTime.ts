/** Wall-clock ↔ UTC helpers using Intl (no extra deps). */

function readWallParts(
  date: Date,
  timeZone: string,
): { year: number; month: number; day: number; hour: number; minute: number } {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(date);

  const get = (type: Intl.DateTimeFormatPartTypes): number => {
    const raw = parts.find((p) => p.type === type)?.value ?? "0";
    return Number(raw);
  };

  return {
    year: get("year"),
    month: get("month"),
    day: get("day"),
    hour: get("hour"),
    minute: get("minute"),
  };
}

function getTimeZoneOffsetMs(date: Date, timeZone: string): number {
  const utc = date.toLocaleString("en-US", { timeZone: "UTC" });
  const zoned = date.toLocaleString("en-US", { timeZone });
  return new Date(zoned).getTime() - new Date(utc).getTime();
}

/** `YYYY-MM-DDTHH:mm` wall time in `timeZone` → UTC `Date`. */
export function wallDateTimeLocalToUtc(dateTimeLocal: string, timeZone: string): Date {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(dateTimeLocal);
  if (!match) {
    return new Date(dateTimeLocal);
  }

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const hour = Number(match[4]);
  const minute = Number(match[5]);

  let utcMs = Date.UTC(year, month - 1, day, hour, minute);
  for (let i = 0; i < 3; i += 1) {
    const offset = getTimeZoneOffsetMs(new Date(utcMs), timeZone);
    utcMs = Date.UTC(year, month - 1, day, hour, minute) - offset;
  }
  return new Date(utcMs);
}

/** UTC instant → `YYYY-MM-DDTHH:mm` for datetime-local in `timeZone`. */
export function utcToWallDateTimeLocal(date: Date, timeZone: string): string {
  const { year, month, day, hour, minute } = readWallParts(date, timeZone);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${year}-${pad(month)}-${pad(day)}T${pad(hour)}:${pad(minute)}`;
}
