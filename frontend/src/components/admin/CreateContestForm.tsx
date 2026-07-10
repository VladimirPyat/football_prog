"use client";

import { useState, type FormEvent } from "react";
import { createContestSchema } from "@/lib/validation/admin";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";

interface CreateContestFormProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: { name: string; slug?: string }) => Promise<void>;
}

export function CreateContestForm({ open, onClose, onSubmit }: CreateContestFormProps) {
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setErrors({});
    const parsed = createContestSchema.safeParse({
      name,
      slug: slug || undefined,
    });
    if (!parsed.success) {
      const next: Record<string, string> = {};
      parsed.error.issues.forEach((i) => {
        next[String(i.path[0])] = i.message;
      });
      setErrors(next);
      return;
    }
    setSubmitting(true);
    try {
      await onSubmit(parsed.data);
      setName("");
      setSlug("");
      onClose();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Новый конкурс" size="lg">
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label
            htmlFor="create-contest-name"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Название
          </label>
          <input
            id="create-contest-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
          />
          {errors.name && <p className="text-sm text-red-600">{errors.name}</p>}
        </div>
        <div>
          <label
            htmlFor="create-contest-slug"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Короткое имя (slug)
          </label>
          <input
            id="create-contest-slug"
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
          />
          <p className="text-xs text-gray-500 mt-1">
            Короткое имя для ссылки (латиница, цифры, дефисы). Необязательно — если пусто, в
            адресе будет только номер конкурса.
          </p>
          {errors.slug && <p className="text-sm text-red-600">{errors.slug}</p>}
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Отмена
          </Button>
          <Button type="submit" disabled={submitting}>
            Создать
          </Button>
        </div>
      </form>
    </Modal>
  );
}
