"use client";

import { useEffect, type ReactNode } from "react";

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  footer?: ReactNode;
  size?: "sm" | "md" | "lg" | "xl";
  testId?: string;
}

const SIZE_CLASSES = {
  sm: "max-w-sm",
  md: "max-w-md",
  lg: "max-w-lg",
  xl: "max-w-6xl",
};

export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
  size = "md",
  testId,
}: ModalProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      data-testid={testId}
    >
      <button
        type="button"
        className="absolute inset-0"
        aria-label="Закрыть"
        onClick={onClose}
      />
      <div
        className={`relative bg-white rounded-lg shadow-lg w-full ${SIZE_CLASSES[size]} max-h-[90vh] overflow-y-auto`}
      >
        {(title || testId) && (
          <div className="flex justify-between items-center px-6 pt-6 pb-2">
            {title ? (
              <h3 className="text-lg font-semibold text-gray-900 pr-4">{title}</h3>
            ) : (
              <span />
            )}
            <button
              type="button"
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 text-xl leading-none shrink-0"
              aria-label="Закрыть"
            >
              ×
            </button>
          </div>
        )}
        <div className={`px-6 ${title ? "pb-4" : "py-6"}`}>{children}</div>
        {footer && <div className="px-6 pb-6 flex justify-end gap-3">{footer}</div>}
      </div>
    </div>
  );
}
