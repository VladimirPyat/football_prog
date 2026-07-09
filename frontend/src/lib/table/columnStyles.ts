/** Two-digit numeric cells — counts (крупный/—/Разница/Исход) and bonuses (1/2/3). Equal width group. */
export const COL_DIGIT2 =
  "w-[3.25rem] min-w-[3.25rem] max-w-[3.5rem] px-1 py-1.5 text-center tabular-nums text-sm";

/** Three-digit totals — без бонусов / бонусы / ИТОГО. Equal width group. */
export const COL_DIGIT3 =
  "w-[4.5rem] min-w-[4.5rem] max-w-[5rem] px-1 py-1.5 text-center tabular-nums text-sm";

export const COL_RANK =
  "w-8 min-w-[2rem] max-w-[2rem] px-0.5 py-1.5 text-center tabular-nums text-sm";

export const COL_NAME =
  "min-w-[7rem] max-w-[11rem] px-1.5 py-1.5 text-left align-middle sticky left-0 bg-inherit z-10";

export function adaptiveNameClass(name: string): string {
  if (name.length > 18) return "text-[10px] leading-tight";
  if (name.length > 14) return "text-xs leading-tight";
  return "text-sm leading-tight";
}
