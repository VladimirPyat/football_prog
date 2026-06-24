"use client";

interface NewsletterPromptModalProps {
  open: boolean;
  title?: string;
  body?: string;
  primaryLabel?: string;
  onClose: () => void;
}

export function NewsletterPromptModal({
  open,
  title = "Отправить напоминание участникам?",
  body = "Функция рассылок будет доступна на Stage 3. Сохранить без рассылки.",
  primaryLabel = "Закрыть",
  onClose,
}: NewsletterPromptModalProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div
        className="bg-white rounded-lg shadow-lg max-w-md w-full p-6"
        role="dialog"
        aria-modal="true"
      >
        <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
        <p className="text-gray-600 mb-6">{body}</p>
        <div className="flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm text-white bg-blue-600 rounded hover:bg-blue-700"
          >
            {primaryLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
