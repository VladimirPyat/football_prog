"use client";

import { useState, type FormEvent } from "react";
import { loginSchema } from "@/lib/validation/login";
import { useAuth } from "@/hooks/useAuth";
import { AppError } from "@/lib/api/client";

interface LoginFormProps {
  onSuccess?: () => void;
}

export function LoginForm({ onSuccess }: LoginFormProps) {
  const { login } = useAuth();
  const [loginName, setLoginName] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setApiError(null);
    setFieldErrors({});

    const parsed = loginSchema.safeParse({ login: loginName, password });
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
      await login(parsed.data.login, parsed.data.password);
      onSuccess?.();
    } catch (err) {
      if (err instanceof AppError) {
        setApiError(err.detail);
      } else {
        setApiError("Ошибка входа");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="login" className="block text-sm font-medium text-gray-700 mb-1">
          Логин
        </label>
        <input
          id="login"
          type="text"
          value={loginName}
          onChange={(e) => setLoginName(e.target.value)}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          autoComplete="username"
        />
        {fieldErrors.login && <p className="text-red-600 text-xs mt-1">{fieldErrors.login}</p>}
      </div>
      <div>
        <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
          Пароль
        </label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          autoComplete="current-password"
        />
        {fieldErrors.password && (
          <p className="text-red-600 text-xs mt-1">{fieldErrors.password}</p>
        )}
      </div>
      {apiError && <p className="text-red-600 text-sm">{apiError}</p>}
      <button
        type="submit"
        disabled={submitting}
        className="w-full bg-blue-600 text-white py-2 px-4 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
      >
        {submitting ? "Вход…" : "Войти"}
      </button>
    </form>
  );
}
