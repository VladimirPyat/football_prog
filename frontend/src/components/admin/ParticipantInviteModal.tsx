"use client";

interface ParticipantInviteModalProps {
  open: boolean;
  login: string;
  tempPassword: string;
  setupUrl: string;
  onClose: () => void;
}

export function ParticipantInviteModal({
  open,
  login,
  tempPassword,
  setupUrl,
  onClose,
}: ParticipantInviteModalProps) {
  if (!open) return null;

  const copyCredentials = async () => {
    const text = `Логин: ${login}\nВременный пароль: ${tempPassword}\nСсылка: ${setupUrl}`;
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      /* clipboard may be unavailable */
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div
        className="bg-white rounded-lg shadow-lg max-w-md w-full p-6"
        role="dialog"
        aria-modal="true"
      >
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Участник приглашён</h3>
        <p className="text-sm text-gray-600 mb-4">Передайте участнику данные для входа:</p>
        <dl className="space-y-2 text-sm mb-6">
          <div>
            <dt className="text-gray-500">Логин</dt>
            <dd className="font-mono font-medium break-all">{login}</dd>
          </div>
          <div>
            <dt className="text-gray-500">Временный пароль</dt>
            <dd className="font-mono font-medium break-all">{tempPassword}</dd>
          </div>
          <div>
            <dt className="text-gray-500">Ссылка для подтверждения</dt>
            <dd className="font-mono text-xs break-all text-blue-700">{setupUrl}</dd>
          </div>
        </dl>
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={copyCredentials}
            className="px-4 py-2 text-sm border border-gray-300 rounded hover:bg-gray-50"
          >
            Копировать
          </button>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm text-white bg-blue-600 rounded hover:bg-blue-700"
          >
            Закрыть
          </button>
        </div>
      </div>
    </div>
  );
}
