"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { ContestPicker } from "@/components/contest/ContestPicker";
import { CreateContestForm } from "@/components/admin/CreateContestForm";
import { apiPost } from "@/lib/api/client";
import { contests } from "@/lib/api/endpoints";
import { useContest } from "@/hooks/useContest";
import { useToast } from "@/hooks/useToast";
import type { ContestOut } from "@/types/api";
import { AppError } from "@/lib/api/client";
import { formatDateRu } from "@/lib/admin/format";

const TABS = [
  { id: "settings", label: "Настройки", href: "/admin/settings/parameters" },
  { id: "rounds", label: "Туры", href: "/admin/rounds" },
  { id: "newsletters", label: "Рассылки", href: "/admin/newsletters" },
  { id: "results", label: "Результаты", href: "/admin/results" },
] as const;

export type AdminTabId = (typeof TABS)[number]["id"];

function resolveActiveTab(pathname: string): AdminTabId {
  if (pathname.startsWith("/admin/rounds")) return "rounds";
  if (pathname.startsWith("/admin/newsletters")) return "newsletters";
  if (pathname.startsWith("/admin/results")) return "results";
  return "settings";
}

export function AdminTopNav() {
  const pathname = usePathname();
  const activeTab = resolveActiveTab(pathname);
  const today = formatDateRu(new Date().toISOString());
  const [showCreate, setShowCreate] = useState(false);
  const { setContestId } = useContest();
  const { showSuccess, showError } = useToast();

  const handleCreateContest = async (data: { name: string; slug?: string }) => {
    try {
      const created = await apiPost<ContestOut>(contests.create(), {
        name: data.name,
        slug: data.slug || undefined,
      });
      sessionStorage.setItem(`contest_setup_hint_${created.id}`, "1");
      await setContestId(created.id, true);
      window.dispatchEvent(new Event("contest-list-changed"));
      setShowCreate(false);
      showSuccess("Конкурс создан");
    } catch (err) {
      showError(err instanceof AppError ? err.detail : "Ошибка создания");
      throw err;
    }
  };

  return (
    <>
      <nav className="bg-white border border-gray-200 rounded-lg mb-6">
        <div className="px-4 py-3 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-4">
            <Link href="/admin" className="font-bold text-gray-900 hover:text-blue-600">
              SportPrognosis
            </Link>
            <span className="text-sm text-gray-500">Сегодня {today}</span>
          </div>
          <div className="flex items-center gap-3">
            <ContestPicker adminMode />
            <button
              type="button"
              onClick={() => setShowCreate(true)}
              className="text-sm text-white bg-blue-600 px-3 py-1.5 rounded hover:bg-blue-700"
            >
              + Новый конкурс
            </button>
          </div>
        </div>
        <div className="border-t border-gray-200 px-4 flex flex-wrap gap-1">
          {TABS.map((tab) => (
            <Link
              key={tab.id}
              href={tab.href}
              className={`px-3 py-2 text-sm border-b-2 ${
                tab.id === activeTab
                  ? "border-blue-600 text-blue-600 font-medium"
                  : "border-transparent text-gray-600 hover:text-gray-900"
              }`}
            >
              {tab.label}
            </Link>
          ))}
        </div>
      </nav>
      <CreateContestForm
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onSubmit={handleCreateContest}
      />
    </>
  );
}
