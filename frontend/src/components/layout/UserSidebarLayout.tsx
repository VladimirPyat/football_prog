"use client";

import { useEffect, type ReactNode } from "react";
import { UserNavMenu } from "@/components/layout/UserNavMenu";
import { useUserNav } from "@/providers/UserNavProvider";

interface UserSidebarLayoutProps {
  children: ReactNode;
}

export function UserSidebarLayout({ children }: UserSidebarLayoutProps) {
  const { mobileMenuOpen, setMobileMenuOpen } = useUserNav();

  useEffect(() => {
    if (!mobileMenuOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMobileMenuOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [mobileMenuOpen, setMobileMenuOpen]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
      {mobileMenuOpen && (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-black/40 lg:hidden"
          aria-label="Закрыть меню"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      <aside
        className={`lg:col-span-1 lg:block lg:static lg:translate-x-0
          fixed top-0 left-0 z-50 h-full w-72 max-w-[85vw] bg-gray-50 shadow-xl
          transform transition-transform duration-200 ease-out lg:shadow-none lg:w-auto lg:h-auto lg:bg-transparent
          ${mobileMenuOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}`}
      >
        <div className="p-4 lg:p-0 h-full overflow-y-auto">
          <UserNavMenu variant="sidebar" onNavigate={() => setMobileMenuOpen(false)} />
        </div>
      </aside>

      <div className="lg:col-span-3 text-base lg:text-sm min-w-0">{children}</div>
    </div>
  );
}
