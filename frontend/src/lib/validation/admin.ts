import { z } from "zod";
import { deadlineErrorMessage, isDeadlineValid } from "@/lib/admin/deadlineRule";

export const createContestSchema = z.object({
  name: z.string().min(1, "Укажите название"),
  slug: z.string().optional(),
});

/** Round-robin home/away: matches per round and total rounds from team count. */
export function deriveRoundRobinStructure(totalTeams: number): {
  matches_per_round: number;
  total_rounds: number;
} {
  return {
    matches_per_round: totalTeams / 2,
    total_rounds: (totalTeams - 1) * 2,
  };
}

export const contestParametersSchema = z
  .object({
    total_teams: z.coerce.number().int().positive(),
    matches_per_round: z.coerce.number().int().positive(),
    total_rounds: z.coerce.number().int().positive(),
    is_round_robin: z.boolean(),
  })
  .superRefine((d, ctx) => {
    if (d.is_round_robin) {
      if (d.matches_per_round !== d.total_teams / 2) {
        ctx.addIssue({
          code: "custom",
          path: ["matches_per_round"],
          message: "Должно быть = команды / 2",
        });
      }
      if (d.total_rounds !== (d.total_teams - 1) * 2) {
        ctx.addIssue({
          code: "custom",
          path: ["total_rounds"],
          message: "Должно быть = (команды − 1) × 2",
        });
      }
    }
  });

export const teamFormSchema = z.object({
  name: z.string().min(1, "Укажите название"),
  short_name: z.string().min(1, "Укажите сокращение").max(4, "До 4 символов"),
});

export const participantInviteSchema = z.object({
  email: z.string().email("Некорректный email"),
  first_name: z.string().min(1, "Укажите имя"),
  last_name: z.string().min(1, "Укажите фамилию"),
  login: z.string().optional(),
});

export function roundBuilderSchema(matchesPerRound: number, rules: Record<string, unknown>) {
  void rules;
  return z
    .object({
      number: z.coerce.number().int().positive(),
      deadline: z.string().min(1, "Укажите дедлайн прогнозов"),
      matches: z
        .array(
          z.object({
            team1_id: z.coerce.number().int().positive(),
            team2_id: z.coerce.number().int().positive(),
            date_time: z.string(),
          }),
        )
        .min(1)
        .max(matchesPerRound),
    })
    .superRefine((d, ctx) => {
      d.matches.forEach((m, i) => {
        if (m.team1_id === m.team2_id) {
          ctx.addIssue({
            code: "custom",
            path: ["matches", i, "team2_id"],
            message: "Команды должны различаться",
          });
        }
        const parsed = Date.parse(m.date_time);
        if (!m.date_time || Number.isNaN(parsed)) {
          ctx.addIssue({
            code: "custom",
            path: ["matches", i, "date_time"],
            message: "Укажите дату и время для каждого матча",
          });
        }
      });
      const ids = d.matches.flatMap((m) => [m.team1_id, m.team2_id]);
      if (new Set(ids).size !== ids.length) {
        ctx.addIssue({
          code: "custom",
          path: ["matches"],
          message: "Команда не может играть дважды в туре",
        });
      }
      const validTimestamps = d.matches
        .map((m) => Date.parse(m.date_time))
        .filter((t) => !Number.isNaN(t));
      if (validTimestamps.length === 0) return;
      const earliest = Math.min(...validTimestamps);
      if (!isDeadlineValid(d.deadline, new Date(earliest).toISOString())) {
        ctx.addIssue({
          code: "custom",
          path: ["deadline"],
          message: deadlineErrorMessage(),
        });
      }
    });
}

/** Match result scores: empty input is invalid (not coerced to 0). */
export function matchResultSchema(maxScore: number) {
  const scoreField = z.union([z.number(), z.literal("")]);

  return z
    .object({
      score1: scoreField,
      score2: scoreField,
    })
    .superRefine((data, ctx) => {
      for (const field of ["score1", "score2"] as const) {
        const val = data[field];
        if (val === "") {
          ctx.addIssue({
            code: "custom",
            path: [field],
            message: "Укажите счёт",
          });
          continue;
        }
        if (!Number.isInteger(val)) {
          ctx.addIssue({
            code: "custom",
            path: [field],
            message: "Счёт должен быть целым числом",
          });
          continue;
        }
        if (val < 0 || val > maxScore) {
          ctx.addIssue({
            code: "custom",
            path: [field],
            message: `Допустимый диапазон: 0–${maxScore}`,
          });
        }
      }
    })
    .transform((data) => ({
      score1: data.score1 as number,
      score2: data.score2 as number,
    }));
}

export const freeTourSchema = z.object({
  deadline: z.string().min(1),
  matches: z
    .array(
      z.object({
        match_id: z.coerce.number().int().positive(),
        new_date_time: z.string().min(1),
      }),
    )
    .min(1, "Выберите хотя бы один матч"),
});

export const tiebreakSchema = z.object({
  points: z.coerce.number().int().min(0),
});

export const createOrganizerSchema = z.object({
  login: z.string().min(1, "Укажите логин"),
  password: z.string().min(8, "Минимум 8 символов"),
  first_name: z.string().min(1, "Укажите имя"),
  last_name: z.string().min(1, "Укажите фамилию"),
  is_temp_password: z.boolean().default(false),
});

export const LOGO_MAX_BYTES = 2 * 1024 * 1024;
export const LOGO_ALLOWED_TYPES = ["image/png", "image/jpeg", "image/gif"];

export function validateLogoFile(file: File): string | null {
  if (!LOGO_ALLOWED_TYPES.includes(file.type)) {
    return "Допустимы PNG, JPG или GIF";
  }
  if (file.size > LOGO_MAX_BYTES) {
    return "Файл не должен превышать 2 МБ";
  }
  return null;
}
