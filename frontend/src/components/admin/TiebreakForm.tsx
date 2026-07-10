"use client";

import { useState, type FormEvent } from "react";
import { tiebreakSchema } from "@/lib/validation/admin";
import { Button } from "@/components/ui/Button";

interface TiebreakFormProps {
  initialPoints: number;
  onSubmit: (points: number) => Promise<void>;
  onCancel: () => void;
}

export function TiebreakForm({ initialPoints, onSubmit, onCancel }: TiebreakFormProps) {
  const [points, setPoints] = useState(initialPoints);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    const parsed = tiebreakSchema.safeParse({ points });
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? "Ошибка");
      return;
    }
    setSubmitting(true);
    try {
      await onSubmit(parsed.data.points);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Очки тай-брейка</label>
        <input
          type="number"
          value={points}
          onChange={(e) => setPoints(Number(e.target.value))}
          min={0}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        />
        {error && <p className="text-sm text-red-600 mt-1">{error}</p>}
      </div>
      <div className="flex gap-2 justify-end">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Отмена
        </Button>
        <Button type="submit" disabled={submitting}>
          Сохранить
        </Button>
      </div>
    </form>
  );
}
