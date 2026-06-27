"use client";

import { AdminPageShell } from "@/components/admin/AdminPageShell";
import { TeamsGrid } from "@/components/admin/TeamsGrid";
import { deriveAdminUiMode } from "@/lib/admin/deriveAdminUiMode";
import { useContestAdmin } from "@/hooks/useContestAdmin";
import { useTeams } from "@/hooks/useTeams";
import { useToast } from "@/hooks/useToast";
import { AppError } from "@/lib/api/client";

export default function AdminSettingsTeamsPage() {
  const { contest, contestId } = useContestAdmin();
  const { teams, createTeam, patchTeam, deleteTeam, uploadLogo } = useTeams(contestId);
  const { showSuccess, showError } = useToast();

  if (!contest) return null;

  const uiMode = deriveAdminUiMode({ contest, round: null });

  return (
    <AdminPageShell title="Настройки" showSettingsNav showSetupLockBanner>
      <TeamsGrid
        teams={teams}
        readonly={uiMode.setupReadonly}
        onCreate={async (data) => {
          try {
            await createTeam(data);
            showSuccess("Команда добавлена");
          } catch (err) {
            showError(err instanceof AppError ? err.detail : "Ошибка");
          }
        }}
        onPatch={async (teamId, data) => {
          try {
            await patchTeam(teamId, data);
            showSuccess("Команда обновлена");
          } catch (err) {
            showError(err instanceof AppError ? err.detail : "Ошибка");
          }
        }}
        onDelete={async (teamId) => {
          try {
            await deleteTeam(teamId);
            showSuccess("Команда удалена");
          } catch (err) {
            showError(err instanceof AppError ? err.detail : "Ошибка");
          }
        }}
        onUploadLogo={async (teamId, file) => {
          try {
            await uploadLogo(teamId, file);
            showSuccess("Логотип загружен");
          } catch (err) {
            showError(err instanceof AppError ? err.detail : "Ошибка загрузки");
          }
        }}
      />
    </AdminPageShell>
  );
}
