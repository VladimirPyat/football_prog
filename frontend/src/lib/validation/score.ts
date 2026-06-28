import { z } from "zod";

/** Single score cell: empty is invalid (not coerced to 0). */
export function scoreInputSchema(maxScore: number) {
  const field = z.union([z.number(), z.literal("")]);
  return field.superRefine((val, ctx) => {
    if (val === "") {
      ctx.addIssue({ code: "custom", message: "Укажите счёт" });
      return;
    }
    if (!Number.isInteger(val) || val < 0 || val > maxScore) {
      ctx.addIssue({ code: "custom", message: `Допустимый диапазон: 0–${maxScore}` });
    }
  });
}

/** Parse raw text input into number | "" — rejects non-numeric. */
export function parseScoreInput(raw: string): number | "" {
  if (raw === "") return "";
  if (!/^\d+$/.test(raw)) return "";
  const n = Number(raw);
  return Number.isInteger(n) ? n : "";
}
