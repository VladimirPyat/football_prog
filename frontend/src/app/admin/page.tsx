"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { LoadingState } from "@/components/ui/LoadingState";

const PLACEHOLDER_LINKS = [
  { label: "Жизненный цикл", href: "#" },
  { label: "Пользователи", href: "#" },
  { label: "Настройки конкурса", href: "#" },
] as const;

export default function AdminDashboardPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading || !user) return;
    if (user.role === "SUPERVISOR") {
      router.replace("/admin/settings/parameters");
    }
  }, [loading, user, router]);

  if (loading || !user) {
    return <LoadingState />;
  }

  if (user.role === "SUPERVISOR") {
    return <LoadingState message="Переход к настройкам…" />;
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Панель администратора</h1>
      <p className="text-gray-600 mb-6">Разделы управления появятся на этапе 2.3.</p>
      <ul className="space-y-3">
        {PLACEHOLDER_LINKS.map((item) => (
          <li key={item.label}>
            <span
              className="text-gray-400 cursor-not-allowed"
              title="Скоро — этап 2.3"
              aria-disabled="true"
            >
              {item.label}
            </span>
            <span className="text-sm text-gray-500 ml-2">— Скоро — этап 2.3</span>
          </li>
        ))}
      </ul>
      <p className="mt-6 text-sm text-gray-500">
        Организаторы:{" "}
        <Link href="/admin/settings/parameters" className="text-blue-600 hover:underline">
          Управление конкурсом
        </Link>
      </p>
    </div>
  );
}
