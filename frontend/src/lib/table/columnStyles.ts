/** Two-digit numeric cells (match points, bonuses, counts ≤99). */
export const COL_DIGIT2 = "w-8 min-w-[2rem] max-w-[2rem] px-0.5 py-1.5 text-center tabular-nums text-sm";

/** Three-digit totals (≤999). */
export const COL_DIGIT3 =
  "w-10 min-w-[2.5rem] max-w-[2.5rem] px-0.5 py-1.5 text-center tabular-nums text-sm font-semibold";

export const COL_RANK = "w-8 min-w-[2rem] max-w-[2rem] px-0.5 py-1.5 text-center tabular-nums text-sm";

export const COL_NAME =
  "min-w-[5.5rem] max-w-[8.5rem] px-1 py-1.5 text-left align-middle sticky left-0 bg-inherit z-10";

export function adaptiveNameClass(name: string): string {
  if (name.length > 18) return "text-[10px] leading-tight";
  if (name.length > 14) return "text-xs leading-tight";
  return "text-sm leading-tight";
}
