"use client";

import { useState } from "react";
import type { ContestOut } from "@/types/api";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";

interface LifecyclePanelProps {
  contest: ContestOut;
  onPause: () => Promise<void>;
  onResume: () => Promise<void>;
  onFinish: () => Promise<void>;
  onDelete: () => Promise<void>;
  onRestore?: () => Promise<void>;
  onRecalculate: () => Promise<void>;
  disabled: boolean;
  showFinishDelete?: boolean;
  restoreAvailable?: boolean;
}

export function LifecyclePanel({
  contest,
  onPause,
  onResume,
  onFinish,
  onDelete,
  onRestore,
  onRecalculate,
  disabled,
  showFinishDelete = true,
  restoreAvailable = false,
}: LifecyclePanelProps) {
  const [confirmAction, setConfirmAction] = useState<
    "pause" | "resume" | "finish" | "delete" | "recalculate" | "restore" | null
  >(null);
  const [working, setWorking] = useState(false);

  const run = async (action: typeof confirmAction) => {
    if (!action) return;
    setWorking(true);
    try {
      if (action === "pause") await onPause();
      if (action === "resume") await onResume();
      if (action === "finish") await onFinish();
      if (action === "delete") await onDelete();
      if (action === "recalculate") await onRecalculate();
      if (action === "restore" && onRestore) await onRestore();
    } finally {
      setWorking(false);
      setConfirmAction(null);
    }
  };

  const messages = {
    pause: {
      title: "Поставить конкурс на паузу?",
      message: "Все операции изменения данных будут заблокированы.",
    },
    resume: {
      title: "Возобновить конкурс?",
      message: "Конкурс снова станет активным.",
    },
    finish: {
      title: "Завершить конкурс?",
      message: "Конкурс будет переведён в статус «Завершён».",
    },
    delete: {
      title: "Удалить конкурс?",
      message:
        "Конкурс будет удалён безвозвратно. Действие возможно только после паузы и истечения grace-периода.",
    },
    recalculate: {
      title: "Пересчитать конкурс?",
      message: "Будет выполнен полный пересчёт очков по всем турам.",
    },
    restore: {
      title: "Восстановить конкурс?",
      message: "Данные конкурса будут восстановлены из последнего снимка.",
    },
  };

  return (
    <div className="space-y-6 max-w-lg">
      <dl className="grid grid-cols-2 gap-2 text-sm">
        <dt className="text-gray-500">Статус</dt>
        <dd className="font-medium">{contest.status}</dd>
        <dt className="text-gray-500">Заблокирован</dt>
        <dd>{contest.is_locked ? "Да" : "Нет"}</dd>
      </dl>

      <div className="flex flex-wrap gap-3">
        {contest.status === "RUNNING" && (
          <button
            type="button"
            disabled={disabled}
            onClick={() => setConfirmAction("pause")}
            className="px-4 py-2 text-sm text-white bg-amber-600 rounded hover:bg-amber-700 disabled:opacity-50"
          >
            Пауза
          </button>
        )}
        {contest.status === "PAUSED" && (
          <button
            type="button"
            disabled={disabled}
            onClick={() => setConfirmAction("resume")}
            className="px-4 py-2 text-sm text-white bg-green-600 rounded hover:bg-green-700 disabled:opacity-50"
          >
            Возобновить
          </button>
        )}
        {contest.status !== "FINISHED" && showFinishDelete && (
          <button
            type="button"
            disabled={disabled}
            onClick={() => setConfirmAction("finish")}
            className="px-4 py-2 text-sm text-white bg-red-600 rounded hover:bg-red-700 disabled:opacity-50"
          >
            Завершить
          </button>
        )}
        <button
          type="button"
          disabled={disabled}
          onClick={() => setConfirmAction("recalculate")}
          className="px-4 py-2 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
        >
          Пересчитать
        </button>
        {showFinishDelete && (
          <button
            type="button"
            disabled={disabled}
            onClick={() => setConfirmAction("delete")}
            className="px-4 py-2 text-sm text-red-600 border border-red-300 rounded hover:bg-red-50 disabled:opacity-50"
          >
            Удалить конкурс
          </button>
        )}
        {restoreAvailable && onRestore && contest.status === "DRAFT" && (
          <button
            type="button"
            disabled={disabled}
            onClick={() => setConfirmAction("restore")}
            className="px-4 py-2 text-sm text-white bg-indigo-600 rounded hover:bg-indigo-700 disabled:opacity-50"
          >
            Восстановить
          </button>
        )}
      </div>

      {confirmAction && (
        <ConfirmDialog
          open
          title={messages[confirmAction].title}
          message={messages[confirmAction].message}
          confirmLabel="Подтвердить"
          danger={confirmAction === "delete" || confirmAction === "finish"}
          onConfirm={() => run(confirmAction)}
          onCancel={() => setConfirmAction(null)}
        />
      )}
      {working && <p className="text-sm text-gray-500">Выполняется…</p>}
    </div>
  );
}
