"use client";

import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { ChangePasswordForm } from "@/components/auth/ChangePasswordForm";

export default function ChangePasswordPage() {
  return (
    <ProtectedRoute requireAuth>
      <ChangePasswordForm />
    </ProtectedRoute>
  );
}
