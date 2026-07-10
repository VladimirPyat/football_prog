"use client";

import { useState } from "react";
import type { ContestOut } from "@/types/api";
import { Button } from "@/components/ui/Button";
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

  const deleteMessage =
    "Конкурс будет скрыт из списка. Администратор может восстановить данные в течение ограниченного времени.";

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
      message: deleteMessage,
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
          <Button variant="warning" disabled={disabled} onClick={() => setConfirmAction("pause")}>
            Пауза
          </Button>
        )}
        {contest.status === "PAUSED" && (
          <Button variant="success" disabled={disabled} onClick={() => setConfirmAction("resume")}>
            Возобновить
          </Button>
        )}
        {contest.status !== "FINISHED" && showFinishDelete && (
          <Button variant="danger" disabled={disabled} onClick={() => setConfirmAction("finish")}>
            Завершить
          </Button>
        )}
        <Button variant="secondary" disabled={disabled} onClick={() => setConfirmAction("recalculate")}>
          Пересчитать
        </Button>
        {showFinishDelete && (
          <Button
            variant="dangerOutline"
            disabled={disabled}
            onClick={() => setConfirmAction("delete")}
          >
            Удалить конкурс
          </Button>
        )}
        {restoreAvailable && onRestore && contest.status === "DRAFT" && (
          <Button variant="indigo" disabled={disabled} onClick={() => setConfirmAction("restore")}>
            Восстановить
          </Button>
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
