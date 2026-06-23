"use client";

import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { useContest } from "@/hooks/useContest";
import { resolveDefaultContestId } from "@/lib/contest/resolveDefaultContestId";

export function ProfileMenu() {
  const { logout } = useAuth();
  const { contestId } = useContest();
  const activeId = contestId ?? resolveDefaultContestId();

  const scrollToContacts = () => {
    document.getElementById("contacts")?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <nav className="bg-white border border-gray-200 rounded-lg p-4 space-y-2">
      <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Меню</h2>
      <ul className="space-y-1">
        <li>
          <button
            type="button"
            onClick={scrollToContacts}
            className="w-full text-left text-sm text-gray-700 hover:text-blue-600 py-1.5"
          >
            Контакты
          </button>
        </li>
        <li>
          <Link href="/contests" className="block text-sm text-gray-700 hover:text-blue-600 py-1.5">
            Конкурсы
          </Link>
        </li>
        <li>
          <span className="block text-sm text-gray-400 py-1.5 cursor-not-allowed">
            Сделать прогноз — Скоро (2.2)
          </span>
        </li>
        <li>
          <Link
            href={`/contest/${activeId}`}
            className="block text-sm text-gray-700 hover:text-blue-600 py-1.5"
          >
            Просмотр результатов
          </Link>
        </li>
        <li>
          <span className="block text-sm text-gray-400 py-1.5">Личная статистика — скоро</span>
        </li>
        <li>
          <button
            type="button"
            onClick={logout}
            className="w-full text-left text-sm text-red-600 hover:text-red-700 py-1.5"
          >
            Выйти
          </button>
        </li>
      </ul>
    </nav>
  );
}
