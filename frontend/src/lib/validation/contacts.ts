import { z } from "zod";

export const contactsSchema = z.object({
  email: z.string().email("Некорректный email").optional().or(z.literal("")),
  vk_id: z.string().optional(),
  tg_id: z.string().optional(),
  notify_enabled: z.boolean(),
});

export type ContactsFormData = z.infer<typeof contactsSchema>;
