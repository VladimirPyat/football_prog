"use client";

import type { ReactNode } from "react";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { AdminTopNav } from "@/components/admin/AdminTopNav";

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <ProtectedRoute requireAuth requireRole="SUPERVISOR" requireNotTempPassword>
      <AdminTopNav />
      {children}
    </ProtectedRoute>
  );
}
