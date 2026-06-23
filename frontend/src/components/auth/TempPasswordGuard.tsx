"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";

/** Redirects authenticated temp-password users to /change-password */
export function TempPasswordGuard() {
  const { isAuthenticated, isTempPassword, loading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (isAuthenticated && isTempPassword && pathname !== "/change-password") {
      router.replace("/change-password");
    }
  }, [loading, isAuthenticated, isTempPassword, pathname, router]);

  return null;
}
