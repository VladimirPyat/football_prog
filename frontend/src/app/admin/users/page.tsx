"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AdminPageShell } from "@/components/admin/AdminPageShell";
import { CreateOrganizerForm } from "@/components/admin/CreateOrganizerForm";
import { useAuth } from "@/hooks/useAuth";
import { apiPost } from "@/lib/api/client";
import { adminUsers } from "@/lib/api/endpoints";
import { useToast } from "@/hooks/useToast";
import { AppError } from "@/lib/api/client";
import { LoadingState } from "@/components/ui/LoadingState";
import type { CreateSupervisorResponse } from "@/types/api";

function UsersContent() {
  const { showSuccess, showError } = useToast();

  return (
    <AdminPageShell title="Пользователи">
      <p className="text-gray-600 mb-6">Создание учётной записи организатора (SUPERVISOR).</p>
      <CreateOrganizerForm
        onSubmit={async (data) => {
          try {
            const res = await apiPost<CreateSupervisorResponse>(
              adminUsers.createSupervisor(),
              data,
            );
            showSuccess(`Организатор создан: ${res.user.login}`);
          } catch (err) {
            showError(err instanceof AppError ? err.detail : "Ошибка создания");
          }
        }}
      />
    </AdminPageShell>
  );
}

export default function AdminUsersPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user && user.role !== "ADMIN") {
      router.replace("/admin");
    }
  }, [loading, user, router]);

  if (loading || !user) return <LoadingState />;
  if (user.role !== "ADMIN") return <LoadingState message="Доступ запрещён" />;

  return <UsersContent />;
}
