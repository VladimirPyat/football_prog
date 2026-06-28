import { assertApiStorageIsUtc } from "@/lib/datetime/config";

/**
 * Parse API/DB timestamps as UTC instants.
 *
 * Policy: `getApiStorageTimeZone()` (default UTC). See `config.ts` and manuals/CONFIG.md.
 * Naive ISO from API is UTC wall clock — not the supervisor display zone.
 */
export function parseApiUtc(iso: string): number {
  assertApiStorageIsUtc();
  if (!iso) return Number.NaN;
  const trimmed = iso.trim();
  if (!trimmed) return Number.NaN;
  const hasOffset = /(?:Z|[+-]\d{2}:\d{2})$/i.test(trimmed);
  return Date.parse(hasOffset ? trimmed : `${trimmed}Z`);
}

export function parseApiUtcDate(iso: string): Date {
  return new Date(parseApiUtc(iso));
}
