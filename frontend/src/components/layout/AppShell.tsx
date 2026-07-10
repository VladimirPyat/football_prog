"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { isSupervisorOrAbove } from "@/lib/auth/guards";
import { LoginModal } from "@/components/layout/LoginModal";
import { ContestPicker } from "@/components/contest/ContestPicker";
import { HeaderDateTime } from "@/components/layout/HeaderDateTime";
import { MobileMenuButton } from "@/components/layout/MobileMenuButton";
import { UserSidebarLayout } from "@/components/layout/UserSidebarLayout";
import { UserNavProvider } from "@/providers/UserNavProvider";
import { Button } from "@/components/ui/Button";

interface AppShellProps {
  children: ReactNode;
}

function AppShellInner({ children }: AppShellProps) {
  const pathname = usePathname();
  const { isAuthenticated, user, logout } = useAuth();
  const [loginOpen, setLoginOpen] = useState(false);
  const isStaff = isSupervisorOrAbove(user?.role ?? null);
  const isUser = isAuthenticated && user?.role === "USER";
  const showHeaderContestPicker = isStaff && !pathname.startsWith("/admin");

  const mainContent = isUser ? <UserSidebarLayout>{children}</UserSidebarLayout> : children;

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2 min-w-0">
            {isUser && <MobileMenuButton />}
            <div className="min-w-0">
              <Link href="/" className="text-lg font-bold text-gray-900 hover:text-blue-600 block">
                Sport Prognosis
              </Link>
              <HeaderDateTime />
            </div>
          </div>
          <div className="flex items-center gap-4 shrink-0">
            {isAuthenticated && showHeaderContestPicker && <ContestPicker />}
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
                  user && (
                    <Link
                      href="/profile"
                      className="text-sm md:text-base text-gray-700 hover:text-blue-600 font-medium"
                      data-testid="header-user-login"
                    >
                      {user.login}
                    </Link>
                  )
                )}
                <Button variant="secondary" size="sm" onClick={logout}>
                  Выйти
                </Button>
              </>
            ) : (
              <Button size="sm" onClick={() => setLoginOpen(true)}>
                Вход
              </Button>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6">{mainContent}</main>

      <footer className="border-t border-gray-200 bg-white py-4 text-center text-sm text-gray-500">
        <p>© 2026 SportPrognosis. Все права защищены.</p>
        {isAuthenticated && user && (
          <p className="mt-1 text-gray-600" data-testid="footer-user-login">
            {user.login}
          </p>
        )}
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

export function AppShell({ children }: AppShellProps) {
  const { isAuthenticated, user } = useAuth();
  const isUser = isAuthenticated && user?.role === "USER";

  if (isUser) {
    return (
      <UserNavProvider>
        <AppShellInner>{children}</AppShellInner>
      </UserNavProvider>
    );
  }

  return <AppShellInner>{children}</AppShellInner>;
}
