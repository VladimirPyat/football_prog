"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { apiGet, apiPost, AppError } from "@/lib/api/client";
import { auth as authEndpoints } from "@/lib/api/endpoints";

interface SetupPreview {
  login: string;
  mode: "password_form" | "confirm_only";
  already_completed: boolean;
}

export function SetupPasswordForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token") ?? "";

  const [preview, setPreview] = useState<SetupPreview | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!token) {
      setError("Ссылка недействительна — отсутствует токен");
      setLoading(false);
      return;
    }
    const load = async () => {
      try {
        const data = await apiGet<SetupPreview>(
          `${authEndpoints.setupPreview()}?token=${encodeURIComponent(token)}`,
          false,
        );
        setPreview(data);
        if (data.already_completed) setDone(true);
      } catch (err) {
        setError(err instanceof AppError ? err.detail : "Ссылка недействительна или истекла");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [token]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (preview?.mode === "password_form") {
      if (newPassword.length < 8) {
        setError("Пароль должен быть не короче 8 символов");
        return;
      }
      if (newPassword !== confirmPassword) {
        setError("Пароли не совпадают");
        return;
      }
    }
    setSubmitting(true);
    try {
      await apiPost(
        authEndpoints.completeSetup(),
        {
          token,
          new_password: preview?.mode === "password_form" ? newPassword : undefined,
        },
        false,
      );
      setDone(true);
    } catch (err) {
      setError(err instanceof AppError ? err.detail : "Ошибка подтверждения");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <p className="text-sm text-gray-500">Загрузка…</p>;
  }

  if (done) {
    return (
      <div className="space-y-4">
        <p className="text-green-700 text-sm">Участие подтверждено. Войдите с вашим паролем.</p>
        <button
          type="button"
          onClick={() => router.push("/")}
          className="w-full bg-blue-600 text-white py-2 px-4 rounded text-sm font-medium hover:bg-blue-700"
        >
          Перейти ко входу
        </button>
      </div>
    );
  }

  if (error && !preview) {
    return <p className="text-red-600 text-sm">{error}</p>;
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      {preview && (
        <p className="text-sm text-gray-600">
          {preview.mode === "confirm_only"
            ? "Подтвердите участие. После подтверждения войдите с паролем из письма."
            : `Установите пароль для участника «${preview.login}».`}
        </p>
      )}
      {preview?.mode === "password_form" && (
        <>
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
              autoComplete="new-password"
            />
          </div>
          <div>
            <label
              htmlFor="confirm_password"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Повторите пароль
            </label>
            <input
              id="confirm_password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
              autoComplete="new-password"
            />
          </div>
        </>
      )}
      {error && <p className="text-red-600 text-sm">{error}</p>}
      <button
        type="submit"
        disabled={submitting}
        className="w-full bg-blue-600 text-white py-2 px-4 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
      >
        {submitting
          ? "Сохранение…"
          : preview?.mode === "confirm_only"
            ? "Подтвердить"
            : "Сохранить"}
      </button>
    </form>
  );
}
