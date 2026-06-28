/**
 * Datetime policy for supervisor UI.
 *
 * | Layer              | Timezone                          |
 * |--------------------|-----------------------------------|
 * | API / DB storage   | UTC (`NEXT_PUBLIC_API_TIMESTAMP_TIMEZONE`) |
 * | datetime-local I/O | `NEXT_PUBLIC_DISPLAY_TIMEZONE` or browser local |
 * | Comparisons        | UTC instants (parseApiUtc)        |
 *
 * See `agent_docs/contracts/frontend_api_integration.md` § Timestamps.
 */

/** Only `UTC` is supported for API/DB semantics today. */
export function getApiStorageTimeZone(): string {
  return process.env.NEXT_PUBLIC_API_TIMESTAMP_TIMEZONE?.trim() || "UTC";
}

/**
 * IANA zone for labels and `<input type="datetime-local">`.
 * Unset → browser local (supervisor device clock).
 */
export function getDisplayTimeZone(): string | undefined {
  const value = process.env.NEXT_PUBLIC_DISPLAY_TIMEZONE?.trim();
  return value || undefined;
}

export function getDateTimeLocale(): string {
  return process.env.NEXT_PUBLIC_DATETIME_LOCALE?.trim() || "ru-RU";
}

export function assertApiStorageIsUtc(): void {
  if (getApiStorageTimeZone() !== "UTC") {
    throw new Error(
      `Unsupported NEXT_PUBLIC_API_TIMESTAMP_TIMEZONE=${getApiStorageTimeZone()}; only UTC is implemented`,
    );
  }
}
