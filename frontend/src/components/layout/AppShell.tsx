"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { isSupervisorOrAbove } from "@/lib/auth/guards";
import { LoginModal } from "@/components/layout/LoginModal";
import { ContestPicker } from "@/components/contest/ContestPicker";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const { isAuthenticated, user, logout } = useAuth();
  const [loginOpen, setLoginOpen] = useState(false);
  const isStaff = isSupervisorOrAbove(user?.role ?? null);

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link href="/" className="text-lg font-bold text-gray-900 hover:text-blue-600">
            Sport Prognosis
          </Link>
          <div className="flex items-center gap-4">
            {isAuthenticated && isStaff && <ContestPicker />}
            {isAuthenticated ? (
              <>
                {isStaff ? (
                  <Link
                    href="/admin"
                    className="text-sm text-gray-700 hover:text-blue-600 font-medium"
                  >
                    Управление
                  </Link>
                ) : (
                  <Link
                    href="/profile"
                    className="text-sm text-gray-700 hover:text-blue-600 font-medium"
                  >
                    Личный кабинет
                  </Link>
                )}
                <button
                  type="button"
                  onClick={logout}
                  className="text-sm text-gray-600 hover:text-red-600 border border-gray-300 rounded px-3 py-1"
                >
                  Выйти
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={() => setLoginOpen(true)}
                className="text-sm bg-blue-600 text-white rounded px-4 py-1.5 hover:bg-blue-700"
              >
                Вход
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-5xl mx-auto w-full px-4 py-6">{children}</main>

      <footer className="border-t border-gray-200 bg-white py-4 text-center text-sm text-gray-500">
        <p>© 2026 SportPrognosis. Все права защищены.</p>
        {!isAuthenticated && (
          <p className="mt-1">
            <Link href="/staff/login" className="text-blue-600 hover:underline">
              Вход для организаторов
            </Link>
          </p>
        )}
      </footer>

      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
    </div>
  );
}
