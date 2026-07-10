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
import { Button } from "@/components/ui/Button";
import type { ContestOut } from "@/types/api";
import { AppError } from "@/lib/api/client";

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
        <div className="border-b border-gray-200 px-4 flex flex-wrap gap-1">
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
        <div className="px-4 py-3 flex flex-wrap items-center justify-end gap-3">
          <ContestPicker adminMode />
          <Button size="sm" onClick={() => setShowCreate(true)}>
            + Новый конкурс
          </Button>
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
