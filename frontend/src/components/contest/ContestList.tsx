"use client";

import type { ContestListItem } from "@/types/api";
import { LoadingState } from "@/components/ui/LoadingState";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusChip } from "@/components/ui/StatusChip";

interface ContestListProps {
  contests: ContestListItem[];
  loading?: boolean;
  onSelect: (id: number) => void;
  title?: string;
}

const STATUS_LABELS: Record<string, string> = {
  DRAFT: "Черновик",
  RUNNING: "Идёт",
  PAUSED: "Приостановлен",
  FINISHED: "Завершён",
};

export function ContestList({
  contests,
  loading = false,
  onSelect,
  title = "Конкурсы",
}: ContestListProps) {
  if (loading) return <LoadingState />;

  if (!contests.length) {
    return <EmptyState message="Нет доступных конкурсов" />;
  }

  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-900 mb-4">{title}</h2>
      <ul className="divide-y divide-gray-200 border border-gray-200 rounded-lg">
        {contests.map((c) => (
          <li key={c.id}>
            <button
              type="button"
              onClick={() => onSelect(c.id)}
              className="w-full text-left px-4 py-3 hover:bg-gray-50 flex justify-between items-center"
            >
              <span className="font-medium text-gray-900">{c.name}</span>
              <StatusChip
                kind="contest"
                status={c.status}
                label={STATUS_LABELS[c.status] ?? c.status}
              />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
