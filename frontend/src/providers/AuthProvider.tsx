"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { apiGet, apiPost } from "@/lib/api/client";
import { auth as authEndpoints } from "@/lib/api/endpoints";
import { clearToken, getToken, setToken, UNAUTHORIZED_EVENT } from "@/lib/auth/token";
import { resolvePostLoginPath } from "@/lib/auth/resolvePostLoginPath";
import { SKIP_HOME_REDIRECT_KEY } from "@/lib/auth/postLoginNavigation";
import type { ChangePasswordRequest, LoginResponse, UserOut } from "@/types/api";

interface AuthContextValue {
  user: UserOut | null;
  loading: boolean;
  isAuthenticated: boolean;
  role: UserOut["role"] | null;
  isTempPassword: boolean;
  login: (login: string, password: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<UserOut | null>;
  changePassword: (oldPassword: string, newPassword: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<UserOut | null>(null);
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
    router.push("/");
  }, [router]);

  const refreshUser = useCallback(async (): Promise<UserOut | null> => {
    const token = getToken();
    if (!token) {
      setUser(null);
      return null;
    }
    try {
      const me = await apiGet<UserOut>(authEndpoints.me());
      setUser(me);
      return me;
    } catch {
      clearToken();
      setUser(null);
      return null;
    }
  }, []);

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await refreshUser();
      setLoading(false);
    };
    void init();
  }, [refreshUser]);

  useEffect(() => {
    const handler = () => logout();
    window.addEventListener(UNAUTHORIZED_EVENT, handler);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, handler);
  }, [logout]);

  const login = useCallback(
    async (loginName: string, password: string) => {
      const res = await apiPost<LoginResponse>(
        authEndpoints.login(),
        { login: loginName, password },
        false,
      );
      setToken(res.access_token);
      const me = await refreshUser();
      if (me) {
        sessionStorage.setItem(SKIP_HOME_REDIRECT_KEY, "1");
        router.replace(resolvePostLoginPath(me));
      }
    },
    [refreshUser, router],
  );

  const changePassword = useCallback(
    async (oldPassword: string, newPassword: string) => {
      const body: ChangePasswordRequest = {
        old_password: oldPassword,
        new_password: newPassword,
      };
      await apiPost<void>(authEndpoints.changePassword(), body);
      const me = await refreshUser();
      if (me) {
        sessionStorage.setItem(SKIP_HOME_REDIRECT_KEY, "1");
        router.replace(resolvePostLoginPath(me));
      }
    },
    [refreshUser, router],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      isAuthenticated: user !== null,
      role: user?.role ?? null,
      isTempPassword: user?.is_temp_password ?? false,
      login,
      logout,
      refreshUser,
      changePassword,
    }),
    [user, loading, login, logout, refreshUser, changePassword],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuthContext(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuthContext must be used within AuthProvider");
  return ctx;
}
