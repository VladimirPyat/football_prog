"use client";

import { useRouter } from "next/navigation";
import { AdminPageShell } from "@/components/admin/AdminPageShell";
import { ContestParametersForm } from "@/components/admin/ContestParametersForm";
import { deriveAdminUiMode } from "@/lib/admin/deriveAdminUiMode";
import { useContestAdmin } from "@/hooks/useContestAdmin";
import { useContest } from "@/hooks/useContest";
import { useToast } from "@/hooks/useToast";
import { AppError, apiGet } from "@/lib/api/client";
import { contests as contestEndpoints } from "@/lib/api/endpoints";
import type { ContestOut } from "@/types/api";

export default function AdminSettingsParametersPage() {
  const { contest, patchContest, refetch } = useContestAdmin();
  const { setContestId } = useContest();
  const router = useRouter();
  const { showSuccess, showError } = useToast();

  if (!contest) return null;

  const uiMode = deriveAdminUiMode({ contest, round: null });

  return (
    <AdminPageShell title="Настройки" showSettingsNav showSetupLockBanner>
      <ContestParametersForm
        contest={contest}
        readonly={uiMode.setupReadonly}
        onSave={async (data) => {
          try {
            await patchContest(data);
            showSuccess("Параметры сохранены");
          } catch (err) {
            showError(err instanceof AppError ? err.detail : "Ошибка сохранения");
          }
        }}
        onValidationError={(message) => showError(message)}
        onLifecycleSuccess={async (action) => {
          if (action === "delete") {
            showSuccess(
              "Конкурс удалён. Администратор может восстановить данные в течение ограниченного времени",
            );
            try {
              const remaining = await apiGet<ContestOut[]>(contestEndpoints.list());
              if (remaining.length > 0) {
                await setContestId(remaining[0].id, true);
                window.dispatchEvent(new Event("contest-list-changed"));
              } else {
                router.replace("/admin/settings/parameters");
              }
            } catch {
              await refetch();
            }
            return;
          }
          await refetch();
          if (action === "start") {
            showSuccess("Конкурс запущен");
          } else {
            showSuccess("Статус конкурса обновлён");
          }
        }}
        onLifecycleError={showError}
      />
    </AdminPageShell>
  );
}
