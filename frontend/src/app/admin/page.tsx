"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { LoadingState } from "@/components/ui/LoadingState";

const ADMIN_LINKS = [
  { label: "Жизненный цикл", href: "/admin/lifecycle" },
  { label: "Пользователи", href: "/admin/users" },
  { label: "Настройки конкурса", href: "/admin/settings/parameters" },
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
      <p className="text-gray-600 mb-6">Управление конкурсом и системными настройками.</p>
      <ul className="space-y-3">
        {ADMIN_LINKS.map((item) => (
          <li key={item.href}>
            <Link href={item.href} className="text-blue-600 hover:underline font-medium">
              {item.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
