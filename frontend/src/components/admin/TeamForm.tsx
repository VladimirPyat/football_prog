"use client";

import { useState, type FormEvent } from "react";
import { teamFormSchema } from "@/lib/validation/admin";

interface TeamFormProps {
  readonly?: boolean;
  initial?: { name: string; short_name: string };
  onSubmit: (data: { name: string; short_name: string }) => Promise<void>;
  onCancel?: () => void;
  submitLabel?: string;
}

export function TeamForm({
  readonly = false,
  initial,
  onSubmit,
  onCancel,
  submitLabel = "Сохранить",
}: TeamFormProps) {
  const [name, setName] = useState(initial?.name ?? "");
  const [shortName, setShortName] = useState(initial?.short_name ?? "");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (readonly) return;
    setErrors({});
    const parsed = teamFormSchema.safeParse({ name, short_name: shortName });
    if (!parsed.success) {
      const next: Record<string, string> = {};
      parsed.error.issues.forEach((i) => {
        const key = String(i.path[0] ?? "form");
        next[key] = i.message;
      });
      setErrors(next);
      return;
    }
    setSubmitting(true);
    try {
      await onSubmit(parsed.data);
      if (!initial) {
        setName("");
        setShortName("");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {!readonly && (
        <p className="text-sm text-gray-500">Доступно только до старта конкурса</p>
      )}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Название</label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={readonly}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm disabled:bg-gray-100"
        />
        {errors.name && <p className="text-sm text-red-600 mt-1">{errors.name}</p>}
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Сокращение (до 4 символов)
        </label>
        <input
          value={shortName}
          onChange={(e) => setShortName(e.target.value)}
          disabled={readonly}
          maxLength={4}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm disabled:bg-gray-100"
        />
        {errors.short_name && <p className="text-sm text-red-600 mt-1">{errors.short_name}</p>}
      </div>
      {!readonly && (
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-2 text-sm text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {submitLabel}
          </button>
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 text-sm border border-gray-300 rounded hover:bg-gray-50"
            >
              Отмена
            </button>
          )}
        </div>
      )}
    </form>
  );
}
