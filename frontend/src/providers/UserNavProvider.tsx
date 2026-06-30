"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

interface UserNavContextValue {
  mobileMenuOpen: boolean;
  setMobileMenuOpen: (open: boolean) => void;
  toggleMobileMenu: () => void;
}

const UserNavContext = createContext<UserNavContextValue | null>(null);

export function UserNavProvider({ children }: { children: ReactNode }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const toggleMobileMenu = useCallback(() => setMobileMenuOpen((v) => !v), []);

  const value = useMemo(
    () => ({ mobileMenuOpen, setMobileMenuOpen, toggleMobileMenu }),
    [mobileMenuOpen, toggleMobileMenu],
  );

  return <UserNavContext.Provider value={value}>{children}</UserNavContext.Provider>;
}

export function useUserNav(): UserNavContextValue {
  const ctx = useContext(UserNavContext);
  if (!ctx) {
    throw new Error("useUserNav must be used within UserNavProvider");
  }
  return ctx;
}
