"use client";

import { useState } from "react";
import {
  formatDateTimeRu,
  fromDatetimeLocal,
  matchStatusLabel,
  toDatetimeLocal,
} from "@/lib/admin/format";
import {
  canCancelMatch,
  canMarkPostponed,
  canRescheduleMatch,
  canRestoreMatchStatus,
  isLongPostponement,
  longPostponementHint,
} from "@/lib/admin/matchScheduleEdit";
import type { MatchOut, MatchStatus } from "@/types/api";

const STATUS_OPTIONS: { value: MatchStatus; label: string }[] = [
  { value: "SCHEDULED", label: "Запланирован" },
  { value: "POSTPONED", label: "Перенесён" },
  { value: "CANCELED", label: "Отменён" },
];

function activeStatusOptions(
  match: MatchOut,
  isAdmin: boolean,
): { value: MatchStatus; label: string }[] {
  if (match.status === "SCHEDULED") return STATUS_OPTIONS;
  if (match.status === "POSTPONED") {
    return isAdmin
      ? STATUS_OPTIONS
      : STATUS_OPTIONS.filter((o) => o.value === "POSTPONED" || o.value === "CANCELED");
  }
  if (match.status === "CANCELED") {
    return isAdmin ? STATUS_OPTIONS : STATUS_OPTIONS.filter((o) => o.value === "CANCELED");
  }
  return STATUS_OPTIONS.filter((o) => o.value === match.status);
}

function canChangeActiveStatus(match: MatchOut, isAdmin: boolean): boolean {
  if (match.status === "SCHEDULED" || match.status === "POSTPONED") return true;
  return canRestoreMatchStatus(match, isAdmin);
}

interface MatchEditorRowProps {
  match: MatchOut;
  /** DRAFT = full editor; ACTIVE = schedule-only; omit = legacy readonly checks */
  roundStatus?: string;
  isAdmin?: boolean;
  canEditStructure: boolean;
  canEditStatusAndDate: boolean;
  teams?: { id: number; name: string }[];
  onChange?: (patch: {
    team1_id?: number;
    team2_id?: number;
    date_time?: string;
    status?: MatchStatus;
  }) => void;
  onRequestAction?: (action: "cancel" | "postpone" | "restore", match: MatchOut) => void;
}

type PendingAction = "cancel" | "postpone" | "restore";

export function MatchEditorRow({
  match,
  roundStatus,
  isAdmin = false,
  canEditStructure,
  canEditStatusAndDate,
  teams = [],
  onChange,
  onRequestAction,
}: MatchEditorRowProps) {
  const isActiveMode = roundStatus === "ACTIVE" && canEditStatusAndDate;
  const [dateWarning, setDateWarning] = useState<string | null>(null);
  const now = new Date();

  const applyPatch = (patch: Parameters<NonNullable<typeof onChange>>[0]) => {
    onChange?.(patch);
  };

  const handleActiveStatusChange = (newStatus: MatchStatus) => {
    if (newStatus === match.status) return;
    if (newStatus === "CANCELED" && canCancelMatch(match)) {
      onRequestAction?.("cancel", match);
    } else if (newStatus === "POSTPONED" && canMarkPostponed(match)) {
      onRequestAction?.("postpone", match);
    } else if (newStatus === "SCHEDULED" && canRestoreMatchStatus(match, isAdmin)) {
      onRequestAction?.("restore", match);
    }
  };

  return (
    <tr className="border-t border-gray-200">
      <td className="px-3 py-2 text-sm">
        {canEditStructure && teams.length > 0 ? (
          <div className="flex items-center gap-1">
            <select
              value={match.team1_id ?? ""}
              onChange={(e) => applyPatch({ team1_id: Number(e.target.value) })}
              className="border border-gray-300 rounded px-1 py-0.5 text-xs"
            >
              <option value="">—</option>
              {teams.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
            <span className="text-gray-400">—</span>
            <select
              value={match.team2_id ?? ""}
              onChange={(e) => applyPatch({ team2_id: Number(e.target.value) })}
              className="border border-gray-300 rounded px-1 py-0.5 text-xs"
            >
              <option value="">—</option>
              {teams.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </div>
        ) : (
          <>
            {match.team1} — {match.team2}
          </>
        )}
      </td>
      <td className="px-3 py-2 text-sm">
        {isActiveMode && canRescheduleMatch(match, now) ? (
          <div className="space-y-1">
            <input
              type="datetime-local"
              key={`${match.id}-${match.date_time}`}
              defaultValue={toDatetimeLocal(match.date_time)}
              onChange={(e) => {
                const value = e.target.value;
                if (!value) return;
                const iso = fromDatetimeLocal(value);
                if (isLongPostponement(match.date_time, iso)) {
                  setDateWarning(longPostponementHint());
                } else {
                  setDateWarning(null);
                }
                applyPatch({ date_time: iso });
              }}
              className="border border-gray-300 rounded px-2 py-1 text-sm"
            />
            {dateWarning && <p className="text-xs text-amber-700">{dateWarning}</p>}
          </div>
        ) : canEditStatusAndDate && !isActiveMode ? (
          <input
            type="datetime-local"
            defaultValue={toDatetimeLocal(match.date_time)}
            onChange={(e) => {
              const value = e.target.value;
              applyPatch({ date_time: value ? fromDatetimeLocal(value) : "" });
            }}
            className="border border-gray-300 rounded px-2 py-1 text-sm"
          />
        ) : (
          formatDateTimeRu(match.date_time)
        )}
      </td>
      <td className="px-3 py-2 text-sm">
        {isActiveMode && canChangeActiveStatus(match, isAdmin) ? (
          <select
            value={match.status}
            onChange={(e) => handleActiveStatusChange(e.target.value as MatchStatus)}
            className="border border-gray-300 rounded px-3 py-1 text-sm"
          >
            {activeStatusOptions(match, isAdmin).map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        ) : isActiveMode ? (
          <select
            value={match.status}
            disabled
            className="border border-gray-300 rounded px-3 py-1 text-sm disabled:bg-gray-100"
          >
            {STATUS_OPTIONS.filter((o) => o.value === match.status).map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        ) : canEditStatusAndDate ? (
          <select
            value={match.status}
            onChange={(e) => applyPatch({ status: e.target.value as MatchStatus })}
            className="border border-gray-300 rounded px-3 py-1 text-sm"
          >
            {STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        ) : (
          matchStatusLabel(match.status)
        )}
      </td>
      {!canEditStructure && !canEditStatusAndDate && (
        <td className="px-3 py-2 text-sm text-gray-400">Только просмотр</td>
      )}
    </tr>
  );
}

export type MatchRowAction = PendingAction;

export function matchActionDialogCopy(
  action: MatchRowAction,
  match: MatchOut,
): { title: string; message: string; danger?: boolean; confirmLabel: string } {
  switch (action) {
    case "cancel":
      return {
        title: "Отменить матч?",
        message: `${match.team1} — ${match.team2}: матч будет помечен как отменён. Участники не получат очки за этот матч.`,
        danger: true,
        confirmLabel: "Отменить матч",
      };
    case "postpone":
      return {
        title: "Перенести матч?",
        message:
          "Матч будет помечен как «Перенесён». Добавьте его в свободный тур с новой датой — он исчезнет из текущего тура.",
        confirmLabel: "Подтвердить",
      };
    case "restore":
      return {
        title: "Восстановить матч?",
        message: "Матч вернётся в статус «Запланирован». Доступно только администратору.",
        confirmLabel: "Восстановить",
      };
  }
}
