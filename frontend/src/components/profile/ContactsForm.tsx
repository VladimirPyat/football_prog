"use client";

import { useEffect, useState, type FormEvent } from "react";
import { contactsSchema } from "@/lib/validation/contacts";
import { useContacts } from "@/hooks/useContacts";
import { useToast } from "@/hooks/useToast";
import { LoadingState } from "@/components/ui/LoadingState";
import { AppError } from "@/lib/api/client";

export function ContactsForm() {
  const { contacts, loading, readonly, save } = useContacts();
  const { showSuccess, showError } = useToast();
  const [email, setEmail] = useState("");
  const [vkId, setVkId] = useState("");
  const [tgId, setTgId] = useState("");
  const [notifyEnabled, setNotifyEnabled] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (contacts) {
      setEmail(contacts.email ?? "");
      setVkId(contacts.vk_id ?? "");
      setTgId(contacts.tg_id ?? "");
      setNotifyEnabled(contacts.notify_enabled);
    }
  }, [contacts]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (readonly) return;
    setFieldErrors({});

    const parsed = contactsSchema.safeParse({
      email: email || "",
      vk_id: vkId || undefined,
      tg_id: tgId || undefined,
      notify_enabled: notifyEnabled,
    });
    if (!parsed.success) {
      const errors: Record<string, string> = {};
      parsed.error.issues.forEach((issue) => {
        const key = issue.path[0]?.toString() ?? "form";
        errors[key] = issue.message;
      });
      setFieldErrors(errors);
      return;
    }

    setSubmitting(true);
    try {
      await save({
        email: parsed.data.email || null,
        vk_id: parsed.data.vk_id || null,
        tg_id: parsed.data.tg_id || null,
        notify_enabled: parsed.data.notify_enabled,
      });
      showSuccess("Контакты сохранены");
    } catch (err) {
      const message = err instanceof AppError ? err.detail : "Ошибка сохранения";
      showError(message);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <LoadingState message="Загрузка контактов…" />;

  return (
    <section id="contacts" className="bg-white border border-gray-200 rounded-lg p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Контакты</h2>
      {readonly && <p className="text-sm text-amber-600 mb-4">Редактирование недоступно</p>}
      <form onSubmit={handleSubmit} className="space-y-4 max-w-md">
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
            Email
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={readonly}
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm disabled:bg-gray-100"
          />
          {fieldErrors.email && <p className="text-red-600 text-xs mt-1">{fieldErrors.email}</p>}
        </div>
        <div>
          <label htmlFor="vk_id" className="block text-sm font-medium text-gray-700 mb-1">
            VK ID
          </label>
          <input
            id="vk_id"
            type="text"
            value={vkId}
            onChange={(e) => setVkId(e.target.value)}
            disabled={readonly}
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm disabled:bg-gray-100"
          />
        </div>
        <div>
          <label htmlFor="tg_id" className="block text-sm font-medium text-gray-700 mb-1">
            Telegram ID
          </label>
          <input
            id="tg_id"
            type="text"
            value={tgId}
            onChange={(e) => setTgId(e.target.value)}
            disabled={readonly}
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm disabled:bg-gray-100"
          />
        </div>
        <div className="flex items-center gap-2">
          <input
            id="notify_enabled"
            type="checkbox"
            checked={notifyEnabled}
            onChange={(e) => setNotifyEnabled(e.target.checked)}
            disabled={readonly}
            className="rounded"
          />
          <label htmlFor="notify_enabled" className="text-sm text-gray-700">
            Получать уведомления
          </label>
        </div>
        {!readonly && (
          <button
            type="submit"
            disabled={submitting}
            className="bg-blue-600 text-white py-2 px-4 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? "Сохранение…" : "Сохранить"}
          </button>
        )}
      </form>
    </section>
  );
}
