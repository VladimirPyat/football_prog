"use client";

import Link from "next/link";
import { ContestPicker } from "@/components/contest/ContestPicker";

const TABS = [
  { id: "settings", label: "Настройки" },
  { id: "rounds", label: "Туры" },
  { id: "newsletters", label: "Рассылки" },
  { id: "results", label: "Результаты" },
] as const;

export type AdminTabId = (typeof TABS)[number]["id"];

interface AdminTopNavProps {
  activeTab?: AdminTabId;
}

export function AdminTopNav({ activeTab = "settings" }: AdminTopNavProps) {
  const today = new Date().toLocaleDateString("ru-RU");

  return (
    <nav className="bg-white border border-gray-200 rounded-lg mb-6">
      <div className="px-4 py-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-4">
          <Link href="/admin" className="font-bold text-gray-900 hover:text-blue-600">
            SportPrognosis
          </Link>
          <span className="text-sm text-gray-500">Сегодня {today}</span>
        </div>
        <div className="flex items-center gap-3">
          <ContestPicker />
        </div>
      </div>
      <div className="border-t border-gray-200 px-4 flex flex-wrap gap-1">
        {TABS.map((tab) => (
          <span
            key={tab.id}
            title="Скоро 2.3"
            className={`px-3 py-2 text-sm border-b-2 ${
              tab.id === activeTab
                ? "border-blue-600 text-blue-600 font-medium"
                : "border-transparent text-gray-400"
            }`}
            aria-disabled="true"
          >
            {tab.label}
          </span>
        ))}
      </div>
    </nav>
  );
}
