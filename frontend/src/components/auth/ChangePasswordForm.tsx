"use client";

import { useState, type FormEvent } from "react";
import { changePasswordSchema } from "@/lib/validation/changePassword";
import { useAuth } from "@/hooks/useAuth";
import { AppError } from "@/lib/api/client";

export function ChangePasswordForm() {
  const { changePassword } = useAuth();
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setApiError(null);
    setFieldErrors({});

    const parsed = changePasswordSchema.safeParse({
      old_password: oldPassword,
      new_password: newPassword,
      confirm,
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
      await changePassword(parsed.data.old_password, parsed.data.new_password);
    } catch (err) {
      if (err instanceof AppError) {
        setApiError(err.detail);
      } else {
        setApiError("Ошибка смены пароля");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="max-w-md mx-auto space-y-4">
      <h1 className="text-xl font-semibold text-gray-900 mb-6">Смена пароля</h1>
      <p className="text-sm text-gray-600 mb-4">
        Для продолжения работы необходимо сменить временный пароль.
      </p>
      <div>
        <label htmlFor="old_password" className="block text-sm font-medium text-gray-700 mb-1">
          Текущий пароль
        </label>
        <input
          id="old_password"
          type="password"
          value={oldPassword}
          onChange={(e) => setOldPassword(e.target.value)}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        />
        {fieldErrors.old_password && (
          <p className="text-red-600 text-xs mt-1">{fieldErrors.old_password}</p>
        )}
      </div>
      <div>
        <label htmlFor="new_password" className="block text-sm font-medium text-gray-700 mb-1">
          Новый пароль
        </label>
        <input
          id="new_password"
          type="password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        />
        {fieldErrors.new_password && (
          <p className="text-red-600 text-xs mt-1">{fieldErrors.new_password}</p>
        )}
      </div>
      <div>
        <label htmlFor="confirm" className="block text-sm font-medium text-gray-700 mb-1">
          Подтверждение
        </label>
        <input
          id="confirm"
          type="password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        />
        {fieldErrors.confirm && <p className="text-red-600 text-xs mt-1">{fieldErrors.confirm}</p>}
      </div>
      {apiError && <p className="text-red-600 text-sm">{apiError}</p>}
      <button
        type="submit"
        disabled={submitting}
        className="w-full bg-blue-600 text-white py-2 px-4 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
      >
        {submitting ? "Сохранение…" : "Сменить пароль"}
      </button>
    </form>
  );
}
