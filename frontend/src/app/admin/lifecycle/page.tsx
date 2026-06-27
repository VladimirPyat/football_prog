"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AdminPageShell } from "@/components/admin/AdminPageShell";
import { LifecyclePanel } from "@/components/admin/LifecyclePanel";
import { useAuth } from "@/hooks/useAuth";
import { useContestAdmin } from "@/hooks/useContestAdmin";
import { deriveAdminUiMode } from "@/lib/admin/deriveAdminUiMode";
import { apiDelete, apiPost } from "@/lib/api/client";
import { contests, contestAdmin } from "@/lib/api/endpoints";
import { useToast } from "@/hooks/useToast";
import { AppError } from "@/lib/api/client";
import { LoadingState } from "@/components/ui/LoadingState";

const TRAINING_MODE = process.env.NEXT_PUBLIC_SUPERVISOR_TRAINING_MODE === "true";

function LifecycleContent() {
  const { contest, contestId, refetch } = useContestAdmin();
  const { user } = useAuth();
  const { showSuccess, showError } = useToast();
  const [restoreAvailable, setRestoreAvailable] = useState(false);

  if (!contest) return <LoadingState />;

  const uiMode = deriveAdminUiMode({ contest, round: null });
  const showFinishDelete = user?.role === "ADMIN" || TRAINING_MODE;

  return (
    <AdminPageShell title="Жизненный цикл">
      <LifecyclePanel
        contest={contest}
        disabled={uiMode.disableAllMutations && contest.status === "FINISHED"}
        showFinishDelete={showFinishDelete}
        restoreAvailable={restoreAvailable}
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
            if (TRAINING_MODE) {
              setRestoreAvailable(true);
              showSuccess("Конкурс сброшен. Восстановление доступно ограниченное время");
            } else {
              showSuccess("Конкурс удалён");
            }
          } catch (err) {
            showError(err instanceof AppError ? err.detail : "Ошибка удаления");
            throw err;
          }
        }}
        onRestore={async () => {
          try {
            await apiPost(contests.restore(contestId), {});
            setRestoreAvailable(false);
            await refetch();
            showSuccess("Конкурс восстановлен");
          } catch (err) {
            showError(err instanceof AppError ? err.detail : "Ошибка восстановления");
            throw err;
          }
        }}
        onRecalculate={async () => {
          await apiPost(contestAdmin.recalculate(contestId), {});
          showSuccess("Пересчёт выполнен");
        }}
      />
    </AdminPageShell>
  );
}

export default function AdminLifecyclePage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) {
      const allowed = user.role === "ADMIN" || (TRAINING_MODE && user.role === "SUPERVISOR");
      if (!allowed) {
        router.replace("/admin");
      }
    }
  }, [loading, user, router]);

  if (loading || !user) return <LoadingState />;

  const allowed = user.role === "ADMIN" || (TRAINING_MODE && user.role === "SUPERVISOR");
  if (!allowed) return <LoadingState message="Доступ запрещён" />;

  return <LifecycleContent />;
}
