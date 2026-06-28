"use client";

import { useState } from "react";
import { apiDelete, apiPost, AppError } from "@/lib/api/client";
import { contests } from "@/lib/api/endpoints";
import { useAuth } from "@/hooks/useAuth";
import type { ContestOut } from "@/types/api";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";

interface ContestLifecycleActionsProps {
  contest: ContestOut;
  /** Persist parameters to DB before start (returns false to abort). */
  onBeforeStart?: () => Promise<boolean>;
  startBlocked?: boolean;
  startBlockReason?: string;
  onSuccess: (action: "pause" | "resume" | "start" | "delete") => Promise<void>;
  onError: (message: string) => void;
}

function canDeleteContest(contest: ContestOut): boolean {
  if (contest.status === "FINISHED") return false;
  if (contest.status === "DRAFT" && !contest.is_locked) return true;
  if (contest.status === "PAUSED") return true;
  return false;
}

function deleteConfirmMessage(contest: ContestOut): string {
  if (contest.status === "DRAFT") {
    return "Конкурс будет скрыт из списка. Администратор может восстановить данные в течение ограниченного времени.";
  }
  return "Конкурс будет скрыт из списка после удаления. Для конкурса в статусе «Идёт» сначала остановите его, затем удалите.";
}

export function ContestLifecycleActions({
  contest,
  onBeforeStart,
  startBlocked = false,
  startBlockReason,
  onSuccess,
  onError,
}: ContestLifecycleActionsProps) {
  const { user } = useAuth();
  const [confirmPause, setConfirmPause] = useState(false);
  const [confirmStart, setConfirmStart] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [working, setWorking] = useState(false);

  const isStaff = user?.role === "ADMIN" || user?.role === "SUPERVISOR";
  const showDelete = isStaff && canDeleteContest(contest);

  const runLifecycle = async (action: "pause" | "resume") => {
    setWorking(true);
    try {
      const path = action === "pause" ? contests.pause(contest.id) : contests.resume(contest.id);
      await apiPost(path, {});
      await onSuccess(action);
    } catch (err) {
      onError(err instanceof AppError ? err.detail : "Ошибка операции");
    } finally {
      setWorking(false);
      setConfirmPause(false);
    }
  };

  const runStart = async () => {
    setWorking(true);
    try {
      if (onBeforeStart) {
        const ok = await onBeforeStart();
        if (!ok) return;
      }
      await apiPost(contests.start(contest.id), {});
      await onSuccess("start");
    } catch (err) {
      onError(err instanceof AppError ? err.detail : "Ошибка запуска");
    } finally {
      setWorking(false);
      setConfirmStart(false);
    }
  };

  const runDelete = async () => {
    setWorking(true);
    try {
      await apiDelete(contests.delete(contest.id), { confirm: "DELETE" });
      await onSuccess("delete");
    } catch (err) {
      onError(err instanceof AppError ? err.detail : "Ошибка удаления");
    } finally {
      setWorking(false);
      setConfirmDelete(false);
    }
  };

  const deleteButton = showDelete ? (
    <button
      type="button"
      disabled={working}
      onClick={() => setConfirmDelete(true)}
      className="px-4 py-2 text-sm font-medium text-red-600 border border-red-300 bg-white rounded-lg shadow hover:bg-red-50 disabled:opacity-50"
    >
      Удалить конкурс
    </button>
  ) : null;

  const deleteDialog = showDelete ? (
    <ConfirmDialog
      open={confirmDelete}
      title="Удалить конкурс?"
      message={deleteConfirmMessage(contest)}
      confirmLabel="Удалить"
      danger
      onConfirm={() => void runDelete()}
      onCancel={() => setConfirmDelete(false)}
    />
  ) : null;

  if (contest.status === "DRAFT") {
    const startDisabled = working || startBlocked;
    const startTitle = startBlocked && startBlockReason ? startBlockReason : undefined;

    return (
      <>
        <div className="fixed bottom-6 right-6 z-10 flex flex-wrap items-center gap-3 justify-end">
          {deleteButton}
          <button
            type="button"
            disabled={startDisabled}
            title={startTitle}
            onClick={() => setConfirmStart(true)}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg shadow hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Запустить конкурс
          </button>
        </div>
        <ConfirmDialog
          open={confirmStart}
          title="Запустить конкурс?"
          message="После запуска нельзя менять число команд, туров, состав участников и правила очков. Неподтверждённые приглашения (статус «Ожидает») будут удалены. Туры можно создать и активировать позже на вкладке «Туры»."
          confirmLabel="Запустить"
          onConfirm={() => void runStart()}
          onCancel={() => setConfirmStart(false)}
        />
        {deleteDialog}
      </>
    );
  }

  if (contest.status === "FINISHED") {
    return null;
  }

  if (contest.status === "RUNNING") {
    return (
      <>
        <div className="fixed bottom-6 right-6 z-10 flex flex-wrap items-center gap-3 justify-end">
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
          message="Конкурс будет приостановлен. После остановки его можно удалить. Редактирование будет недоступно до возобновления."
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
      <>
        <div className="fixed bottom-6 right-6 z-10 flex flex-wrap items-center gap-3 justify-end">
          {deleteButton}
          <button
            type="button"
            disabled={working}
            onClick={() => runLifecycle("resume")}
            className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg shadow hover:bg-green-700 disabled:opacity-50"
          >
            Запустить конкурс
          </button>
        </div>
        {deleteDialog}
      </>
    );
  }

  return null;
}
