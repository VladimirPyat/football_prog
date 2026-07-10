"use client";

import { LoginForm } from "@/components/auth/LoginForm";
import { Modal } from "@/components/ui/Modal";

interface LoginModalProps {
  open: boolean;
  onClose: () => void;
}

export function LoginModal({ open, onClose }: LoginModalProps) {
  return (
    <Modal open={open} onClose={onClose} title="Вход" size="md" testId="login-modal">
      <LoginForm onSuccess={onClose} />
    </Modal>
  );
}
