"use client";

import { useState, type FormEvent } from "react";
import { createOrganizerSchema } from "@/lib/validation/admin";
import { Button } from "@/components/ui/Button";

interface CreateOrganizerFormProps {
  onSubmit: (data: {
    login: string;
    password: string;
    first_name: string;
    last_name: string;
    is_temp_password: boolean;
  }) => Promise<void>;
}

export function CreateOrganizerForm({ onSubmit }: CreateOrganizerFormProps) {
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [isTempPassword, setIsTempPassword] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setErrors({});
    const parsed = createOrganizerSchema.safeParse({
      login,
      password,
      first_name: firstName,
      last_name: lastName,
      is_temp_password: isTempPassword,
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
      setLogin("");
      setPassword("");
      setFirstName("");
      setLastName("");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 max-w-md">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Логин</label>
        <input
          value={login}
          onChange={(e) => setLogin(e.target.value)}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        />
        {errors.login && <p className="text-sm text-red-600">{errors.login}</p>}
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Пароль</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        />
        {errors.password && <p className="text-sm text-red-600">{errors.password}</p>}
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Имя</label>
          <input
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Фамилия</label>
          <input
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
          />
        </div>
      </div>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={isTempPassword}
          onChange={(e) => setIsTempPassword(e.target.checked)}
        />
        Временный пароль
      </label>
      <Button type="submit" disabled={submitting}>
        Создать организатора
      </Button>
    </form>
  );
}
