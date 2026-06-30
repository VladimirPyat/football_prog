"use client";

import { useEffect, type ReactNode } from "react";

interface DetailModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}

export function DetailModal({ open, onClose, title, children }: DetailModalProps) {
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
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
      <button
        type="button"
        className="absolute inset-0 bg-black/50"
        aria-label="Закрыть"
        onClick={onClose}
      />
      <div
        className="relative bg-white rounded-t-xl sm:rounded-lg shadow-xl w-full sm:max-w-lg max-h-[85vh] overflow-y-auto mx-0 sm:mx-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby="detail-modal-title"
        data-testid="detail-modal"
      >
        <div className="sticky top-0 bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
          <h2 id="detail-modal-title" className="text-base font-semibold text-gray-900 pr-4">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none shrink-0"
            aria-label="Закрыть"
          >
            ×
          </button>
        </div>
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
}
