"use client";

import { useState, type FormEvent } from "react";
import { participantInviteSchema } from "@/lib/validation/admin";

interface ParticipantInviteFormProps {
  disabled?: boolean;
  onSubmit: (data: {
    email: string;
    first_name: string;
    last_name: string;
    login?: string;
  }) => Promise<void>;
}

export function ParticipantInviteForm({ disabled = false, onSubmit }: ParticipantInviteFormProps) {
  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [login, setLogin] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (disabled) return;
    setErrors({});
    const parsed = participantInviteSchema.safeParse({
      email,
      first_name: firstName,
      last_name: lastName,
      login: login || undefined,
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
      setEmail("");
      setFirstName("");
      setLastName("");
      setLogin("");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-3 max-w-md border border-gray-200 rounded-lg p-4"
    >
      <h3 className="text-sm font-semibold text-gray-900">Пригласить участника</h3>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={disabled}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm disabled:bg-gray-100"
        />
        {errors.email && <p className="text-sm text-red-600">{errors.email}</p>}
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Имя</label>
          <input
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            disabled={disabled}
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm disabled:bg-gray-100"
          />
          {errors.first_name && <p className="text-sm text-red-600">{errors.first_name}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Фамилия</label>
          <input
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
            disabled={disabled}
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm disabled:bg-gray-100"
          />
          {errors.last_name && <p className="text-sm text-red-600">{errors.last_name}</p>}
        </div>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Логин (необязательно)
        </label>
        <input
          value={login}
          onChange={(e) => setLogin(e.target.value)}
          disabled={disabled}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm disabled:bg-gray-100"
        />
      </div>
      <button
        type="submit"
        disabled={disabled || submitting}
        className="px-4 py-2 text-sm text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50"
      >
        Пригласить
      </button>
    </form>
  );
}
