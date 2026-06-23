import { z } from "zod";

export const changePasswordSchema = z
  .object({
    old_password: z.string().min(1, "Введите текущий пароль"),
    new_password: z.string().min(8, "Минимум 8 символов"),
    confirm: z.string().min(1, "Подтвердите пароль"),
  })
  .refine((d) => d.new_password === d.confirm, {
    path: ["confirm"],
    message: "Пароли не совпадают",
  });

export type ChangePasswordFormData = z.infer<typeof changePasswordSchema>;
