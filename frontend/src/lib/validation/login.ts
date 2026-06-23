import { z } from "zod";

export const loginSchema = z.object({
  login: z.string().min(1, "Введите логин"),
  password: z.string().min(1, "Введите пароль"),
});

export type LoginFormData = z.infer<typeof loginSchema>;
