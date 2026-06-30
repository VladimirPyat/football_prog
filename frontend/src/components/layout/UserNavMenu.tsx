"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { useContest } from "@/hooks/useContest";
import { useRounds } from "@/hooks/useRounds";
import { resolveDefaultContestId } from "@/lib/contest/resolveDefaultContestId";

interface UserNavMenuProps {
  variant?: "sidebar" | "dropdown";
  onNavigate?: () => void;
}

export function UserNavMenu({ variant = "sidebar", onNavigate }: UserNavMenuProps) {
  const { logout } = useAuth();
  const { contestId } = useContest();
  const activeId = contestId ?? resolveDefaultContestId();
  const { activeRound } = useRounds(activeId);
  const pathname = usePathname();

  const predictHref = activeRound != null ? `/contest/${activeId}/predict/${activeRound.id}` : null;

  const linkClass =
    variant === "dropdown"
      ? "block text-base md:text-sm text-gray-700 hover:text-blue-600 hover:bg-gray-50 px-3 py-2 rounded"
      : "block text-base lg:text-sm text-gray-700 hover:text-blue-600 py-2 lg:py-1.5";

  const handleContacts = () => {
    onNavigate?.();
    if (pathname === "/profile") {
      document.getElementById("contacts")?.scrollIntoView({ behavior: "smooth" });
    } else {
      window.location.href = "/profile#contacts";
    }
  };

  const wrapperClass =
    variant === "sidebar"
      ? "bg-white border border-gray-200 rounded-lg p-4 space-y-1"
      : "py-1";

  return (
    <nav className={wrapperClass} data-testid="user-nav-menu">
      {variant === "sidebar" && (
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Меню</h2>
      )}
      <ul className="space-y-0.5">
        <li>
          <button type="button" onClick={handleContacts} className={`w-full text-left ${linkClass}`}>
            Контакты
          </button>
        </li>
        <li>
          {predictHref ? (
            <Link href={predictHref} className={linkClass} onClick={onNavigate}>
              Сделать прогноз
            </Link>
          ) : (
            <span
              className={`block text-base lg:text-sm text-gray-400 py-2 lg:py-1.5 cursor-not-allowed`}
              title="Нет активного тура для прогнозов"
            >
              Сделать прогноз
            </span>
          )}
        </li>
        <li>
          <Link href={`/contest/${activeId}`} className={linkClass} onClick={onNavigate}>
            Просмотр результатов
          </Link>
        </li>
        <li>
          <span className={`block text-base lg:text-sm text-gray-400 py-2 lg:py-1.5`}>
            Личная статистика — скоро
          </span>
        </li>
        {variant === "sidebar" && (
          <li>
            <button
              type="button"
              onClick={() => {
                onNavigate?.();
                void logout();
              }}
              className="w-full text-left text-base lg:text-sm text-red-600 hover:text-red-700 py-2 lg:py-1.5"
            >
              Выйти
            </button>
          </li>
        )}
      </ul>
    </nav>
  );
}
