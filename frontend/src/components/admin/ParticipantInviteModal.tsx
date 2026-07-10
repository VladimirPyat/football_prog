"use client";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";

interface ParticipantInviteModalProps {
  open: boolean;
  login: string;
  setupUrl: string;
  onClose: () => void;
}

export function ParticipantInviteModal({
  open,
  login,
  setupUrl,
  onClose,
}: ParticipantInviteModalProps) {
  const copyCredentials = async () => {
    const text = `Логин: ${login}\nСсылка: ${setupUrl}`;
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      /* clipboard may be unavailable */
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Участник приглашён"
      size="md"
      footer={
        <>
          <Button variant="secondary" onClick={() => void copyCredentials()}>
            Копировать
          </Button>
          <Button onClick={onClose}>Закрыть</Button>
        </>
      }
    >
      <p className="text-sm text-gray-600 mb-4">
        Передайте участнику логин и ссылку для подтверждения. По ссылке участник задаст пароль и
        примет участие в конкурсе.
      </p>
      <dl className="space-y-2 text-sm">
        <div>
          <dt className="text-gray-500">Логин</dt>
          <dd className="font-mono font-medium break-all">{login}</dd>
        </div>
        <div>
          <dt className="text-gray-500">Ссылка для подтверждения</dt>
          <dd className="font-mono text-xs break-all text-blue-700">{setupUrl}</dd>
        </div>
      </dl>
    </Modal>
  );
}
