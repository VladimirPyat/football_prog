"use client";

import { useState } from "react";
import { AdminPageShell } from "@/components/admin/AdminPageShell";
import { ParticipantInviteForm } from "@/components/admin/ParticipantInviteForm";
import { ParticipantInviteModal } from "@/components/admin/ParticipantInviteModal";
import { ParticipantsTable } from "@/components/admin/ParticipantsTable";
import { deriveAdminUiMode } from "@/lib/admin/deriveAdminUiMode";
import { useAuth } from "@/hooks/useAuth";
import { useContestAdmin } from "@/hooks/useContestAdmin";
import { useParticipants } from "@/hooks/useParticipants";
import { useToast } from "@/hooks/useToast";
import { AppError } from "@/lib/api/client";

export default function AdminSettingsParticipantsPage() {
  const { contest, contestId } = useContestAdmin();
  const { participants, invite, remove, setTiebreak } = useParticipants(contestId);
  const { role } = useAuth();
  const { showSuccess, showError } = useToast();
  const [inviteModal, setInviteModal] = useState<{
    login: string;
    temp_password: string;
    setup_url: string;
  } | null>(null);

  if (!contest) return null;

  const uiMode = deriveAdminUiMode({ contest, round: null });

  return (
    <AdminPageShell title="Настройки" showSettingsNav showSetupLockBanner>
      <div className="space-y-6">
        <ParticipantInviteForm
          disabled={uiMode.setupReadonly}
          onSubmit={async (data) => {
            try {
              const res = await invite(data);
              setInviteModal({
                login: res.login,
                temp_password: res.temp_password,
                setup_url: res.setup_url,
              });
              showSuccess("Участник приглашён");
            } catch (err) {
              showError(err instanceof AppError ? err.detail : "Ошибка приглашения");
            }
          }}
        />
        <ParticipantsTable
          participants={participants}
          readonly={uiMode.setupReadonly}
          isAdmin={role === "SUPPORT"}
          onDelete={async (userId) => {
            try {
              await remove(userId);
              showSuccess("Участник удалён");
            } catch (err) {
              showError(err instanceof AppError ? err.detail : "Ошибка удаления");
            }
          }}
          onTiebreak={async (userId, points) => {
            try {
              await setTiebreak(userId, points);
              showSuccess("Тай-брейк сохранён");
            } catch (err) {
              showError(err instanceof AppError ? err.detail : "Ошибка");
            }
          }}
        />
      </div>
      {inviteModal && (
        <ParticipantInviteModal
          open
          login={inviteModal.login}
          setupUrl={inviteModal.setup_url}
          onClose={() => setInviteModal(null)}
        />
      )}
    </AdminPageShell>
  );
}
