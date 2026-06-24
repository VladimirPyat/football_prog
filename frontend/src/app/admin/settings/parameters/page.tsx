"use client";

import { AdminPageShell } from "@/components/admin/AdminPageShell";
import { ContestParametersForm } from "@/components/admin/ContestParametersForm";
import { deriveAdminUiMode } from "@/lib/admin/deriveAdminUiMode";
import { useContestAdmin } from "@/hooks/useContestAdmin";
import { useToast } from "@/hooks/useToast";
import { AppError } from "@/lib/api/client";

export default function AdminSettingsParametersPage() {
  const { contest, patchContest } = useContestAdmin();
  const { showSuccess, showError } = useToast();

  if (!contest) return null;

  const uiMode = deriveAdminUiMode({ contest, round: null });

  return (
    <AdminPageShell title="Настройки" showSettingsNav>
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
      />
    </AdminPageShell>
  );
}
