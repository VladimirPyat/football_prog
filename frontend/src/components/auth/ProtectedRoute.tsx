"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { LoadingState } from "@/components/ui/LoadingState";
import type { UserRole } from "@/types/api";
import { hasMinRole } from "@/lib/auth/guards";
import { resolvePostLoginPath } from "@/lib/auth/resolvePostLoginPath";

interface ProtectedRouteProps {
  children: ReactNode;
  requireAuth?: boolean;
  requireRole?: UserRole;
  requireNotTempPassword?: boolean;
}

export function ProtectedRoute({
  children,
  requireAuth = false,
  requireRole,
  requireNotTempPassword = false,
}: ProtectedRouteProps) {
  const { user, loading, isAuthenticated, isTempPassword } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (loading) return;

    if (requireAuth && !isAuthenticated) {
      router.replace("/");
      return;
    }

    if (requireRole === "USER" && user && user.role !== "USER") {
      router.replace("/admin");
      return;
    }

    if (requireRole && user && !hasMinRole(user.role, requireRole)) {
      router.replace("/");
      return;
    }

    if (isAuthenticated && isTempPassword && pathname !== "/change-password") {
      router.replace("/change-password");
      return;
    }

    if (requireNotTempPassword && isTempPassword) {
      router.replace("/change-password");
      return;
    }

    if (pathname === "/change-password" && isAuthenticated && !isTempPassword && user) {
      router.replace(resolvePostLoginPath(user));
      return;
    }

    setReady(true);
  }, [
    loading,
    isAuthenticated,
    isTempPassword,
    requireAuth,
    requireRole,
    requireNotTempPassword,
    user,
    router,
    pathname,
  ]);

  if (loading || !ready) {
    return <LoadingState />;
  }

  return <>{children}</>;
}
