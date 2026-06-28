"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AdminPageShell } from "@/components/admin/AdminPageShell";
import { DeletedContestsPanel } from "@/components/admin/DeletedContestsPanel";
import { LifecyclePanel } from "@/components/admin/LifecyclePanel";
import { useAuth } from "@/hooks/useAuth";
import { useContestAdmin } from "@/hooks/useContestAdmin";
import { deriveAdminUiMode } from "@/lib/admin/deriveAdminUiMode";
import { apiDelete, apiPost } from "@/lib/api/client";
import { contests, contestAdmin } from "@/lib/api/endpoints";
import { useToast } from "@/hooks/useToast";
import { AppError } from "@/lib/api/client";
import { LoadingState } from "@/components/ui/LoadingState";

function LifecycleContent() {
  const { contest, contestId, refetch } = useContestAdmin();
  const { showSuccess, showError } = useToast();

  if (!contest) return <LoadingState />;

  const uiMode = deriveAdminUiMode({ contest, round: null });

  return (
    <AdminPageShell title="Жизненный цикл">
      <section className="mb-10">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Текущий конкурс</h2>
        <LifecyclePanel
          contest={contest}
          disabled={uiMode.disableAllMutations && contest.status === "FINISHED"}
          showFinishDelete={true}
          onPause={async () => {
            await apiPost(contests.pause(contestId), {});
            await refetch();
            showSuccess("Конкурс на паузе");
          }}
          onResume={async () => {
            await apiPost(contests.resume(contestId), {});
            await refetch();
            showSuccess("Конкурс возобновлён");
          }}
          onFinish={async () => {
            await apiPost(contests.finish(contestId), {});
            await refetch();
            showSuccess("Конкурс завершён");
          }}
          onDelete={async () => {
            try {
              await apiDelete(contests.delete(contestId), { confirm: "DELETE" });
              await refetch();
              window.dispatchEvent(new Event("contest-list-changed"));
              showSuccess(
                "Конкурс удалён и скрыт из списка. Администратор может восстановить данные в течение ограниченного времени",
              );
            } catch (err) {
              showError(err instanceof AppError ? err.detail : "Ошибка удаления");
              throw err;
            }
          }}
          onRecalculate={async () => {
            await apiPost(contestAdmin.recalculate(contestId), {});
            showSuccess("Пересчёт выполнен");
          }}
        />
      </section>

      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Удалённые конкурсы</h2>
        <DeletedContestsPanel
          onRestored={async () => {
            await refetch();
          }}
          onError={showError}
          onSuccess={showSuccess}
        />
      </section>
    </AdminPageShell>
  );
}

export default function AdminLifecyclePage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user && user.role !== "ADMIN") {
      router.replace("/admin");
    }
  }, [loading, user, router]);

  if (loading || !user) return <LoadingState />;

  if (user.role !== "ADMIN") {
    return <LoadingState message="Доступ только для администратора" />;
  }

  return <LifecycleContent />;
}
