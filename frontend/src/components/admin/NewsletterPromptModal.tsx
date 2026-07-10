"use client";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";

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
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      size="md"
      footer={<Button onClick={onClose}>{primaryLabel}</Button>}
    >
      <p className="text-gray-600">{body}</p>
    </Modal>
  );
}
