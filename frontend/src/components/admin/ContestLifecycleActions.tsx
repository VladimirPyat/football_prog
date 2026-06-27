"use client";

import Link from "next/link";
import { useState } from "react";
import { apiPost, AppError } from "@/lib/api/client";
import { contests } from "@/lib/api/endpoints";
import type { ContestOut } from "@/types/api";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";

interface ContestLifecycleActionsProps {
  contest: ContestOut;
  onSuccess: () => Promise<void>;
  onError: (message: string) => void;
}

export function ContestLifecycleActions({
  contest,
  onSuccess,
  onError,
}: ContestLifecycleActionsProps) {
  const [confirmPause, setConfirmPause] = useState(false);
  const [working, setWorking] = useState(false);

  const runLifecycle = async (action: "pause" | "resume") => {
    setWorking(true);
    try {
      const path = action === "pause" ? contests.pause(contest.id) : contests.resume(contest.id);
      await apiPost(path, {});
      await onSuccess();
    } catch (err) {
      onError(err instanceof AppError ? err.detail : "Ошибка операции");
    } finally {
      setWorking(false);
      setConfirmPause(false);
    }
  };

  if (contest.status === "DRAFT") {
    return (
      <div className="fixed bottom-6 right-6 z-10">
        <Link
          href="/admin/rounds"
          className="inline-flex px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg shadow hover:bg-blue-700"
        >
          Перейти к турам для запуска
        </Link>
      </div>
    );
  }

  if (contest.status === "FINISHED") {
    return null;
  }

  if (contest.status === "RUNNING") {
    return (
      <>
        <div className="fixed bottom-6 right-6 z-10">
          <button
            type="button"
            disabled={working}
            onClick={() => setConfirmPause(true)}
            className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg shadow hover:bg-red-700 disabled:opacity-50"
          >
            Остановить конкурс
          </button>
        </div>
        <ConfirmDialog
          open={confirmPause}
          title="Остановить конкурс?"
          message="Конкурс будет приостановлен. Редактирование будет недоступно до возобновления."
          confirmLabel="Остановить"
          danger
          onConfirm={() => runLifecycle("pause")}
          onCancel={() => setConfirmPause(false)}
        />
      </>
    );
  }

  if (contest.status === "PAUSED") {
    return (
      <div className="fixed bottom-6 right-6 z-10">
        <button
          type="button"
          disabled={working}
          onClick={() => runLifecycle("resume")}
          className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg shadow hover:bg-green-700 disabled:opacity-50"
        >
          Запустить конкурс
        </button>
      </div>
    );
  }

  return null;
}
