"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { label: "Параметры", href: "/admin/settings/parameters" },
  { label: "Участники", href: "/admin/settings/participants" },
  { label: "Команды", href: "/admin/settings/teams" },
] as const;

export function SettingsSubNav() {
  const pathname = usePathname();

  return (
    <nav className="flex flex-wrap gap-1 border-b border-gray-200 mb-6">
      {TABS.map((tab) => {
        const active = pathname === tab.href;
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={`px-4 py-2 text-sm border-b-2 -mb-px ${
              active
                ? "border-blue-600 text-blue-600 font-medium"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
