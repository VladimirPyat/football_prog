"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiPost, AppError } from "@/lib/api/client";
import { contests } from "@/lib/api/endpoints";
import type { DeletedContestOut } from "@/types/api";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { LoadingState } from "@/components/ui/LoadingState";

interface DeletedContestsPanelProps {
  onRestored: () => void;
  onError: (message: string) => void;
  onSuccess: (message: string) => void;
}

function formatDeletedAt(iso: string): string {
  try {
    return new Date(iso).toLocaleString("ru-RU");
  } catch {
    return iso;
  }
}

export function DeletedContestsPanel({
  onRestored,
  onError,
  onSuccess,
}: DeletedContestsPanelProps) {
  const [items, setItems] = useState<DeletedContestOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [restoreId, setRestoreId] = useState<number | null>(null);
  const [working, setWorking] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiGet<DeletedContestOut[]>(contests.deleted());
      setItems(data);
    } catch (err) {
      onError(err instanceof AppError ? err.detail : "Не удалось загрузить удалённые конкурсы");
    } finally {
      setLoading(false);
    }
  }, [onError]);

  useEffect(() => {
    void load();
  }, [load]);

  const runRestore = async () => {
    if (restoreId == null) return;
    setWorking(true);
    try {
      await apiPost(contests.restore(restoreId), {});
      showSuccessLocal();
      setRestoreId(null);
      await load();
      onRestored();
      window.dispatchEvent(new Event("contest-list-changed"));
    } catch (err) {
      onError(err instanceof AppError ? err.detail : "Ошибка восстановления");
    } finally {
      setWorking(false);
    }
  };

  const showSuccessLocal = () => {
    onSuccess("Конкурс восстановлен");
  };

  if (loading) {
    return <LoadingState message="Загрузка удалённых конкурсов…" />;
  }

  if (items.length === 0) {
    return (
      <p className="text-sm text-gray-500">
        Нет удалённых конкурсов. После soft-delete конкурсы скрываются из списка; здесь их может
        восстановить только администратор (пока действует окно снимка).
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600">
        Конкурсы, скрытые после удаления супервизором. Восстановление доступно только администратору
        и только пока не истёк срок снимка.
      </p>
      <ul className="divide-y divide-gray-200 border border-gray-200 rounded-lg overflow-hidden">
        {items.map((item) => (
          <li
            key={item.id}
            className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 bg-white"
          >
            <div>
              <p className="font-medium text-gray-900">
                #{item.id} — {item.name}
              </p>
              <p className="text-sm text-gray-500">Удалён: {formatDeletedAt(item.deleted_at)}</p>
            </div>
            {item.restore_available ? (
              <button
                type="button"
                disabled={working}
                onClick={() => setRestoreId(item.id)}
                className="px-3 py-1.5 text-sm text-white bg-indigo-600 rounded hover:bg-indigo-700 disabled:opacity-50"
              >
                Восстановить
              </button>
            ) : (
              <span className="text-sm text-gray-400">Снимок недоступен</span>
            )}
          </li>
        ))}
      </ul>

      {restoreId != null && (
        <ConfirmDialog
          open
          title="Восстановить конкурс?"
          message={`Конкурс #${restoreId} будет восстановлен из последнего снимка и снова появится в списке.`}
          confirmLabel="Восстановить"
          onConfirm={() => void runRestore()}
          onCancel={() => setRestoreId(null)}
        />
      )}
    </div>
  );
}
