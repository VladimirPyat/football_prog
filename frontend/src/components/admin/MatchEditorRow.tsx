"use client";

import {
  formatDateTimeRu,
  fromDatetimeLocal,
  matchStatusLabel,
  toDatetimeLocal,
} from "@/lib/admin/format";
import type { MatchOut, MatchStatus } from "@/types/api";

interface MatchEditorRowProps {
  match: MatchOut;
  canEditStructure: boolean;
  canEditStatusAndDate: boolean;
  teams?: { id: number; name: string }[];
  onChange?: (patch: {
    team1_id?: number;
    team2_id?: number;
    date_time?: string;
    status?: MatchStatus;
  }) => void;
}

const STATUS_OPTIONS: { value: MatchStatus; label: string }[] = [
  { value: "SCHEDULED", label: "Запланирован" },
  { value: "POSTPONED", label: "Перенесён" },
  { value: "CANCELED", label: "Отменён" },
];

export function MatchEditorRow({
  match,
  canEditStructure,
  canEditStatusAndDate,
  teams = [],
  onChange,
}: MatchEditorRowProps) {
  return (
    <tr className="border-t border-gray-200">
      <td className="px-3 py-2 text-sm">
        {canEditStructure && teams.length > 0 ? (
          <div className="flex items-center gap-1">
            <select
              value={match.team1_id ?? ""}
              onChange={(e) => onChange?.({ team1_id: Number(e.target.value) })}
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
              onChange={(e) => onChange?.({ team2_id: Number(e.target.value) })}
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
        {canEditStatusAndDate ? (
          <input
            type="datetime-local"
            defaultValue={toDatetimeLocal(match.date_time)}
            onChange={(e) => onChange?.({ date_time: fromDatetimeLocal(e.target.value) })}
            className="border border-gray-300 rounded px-2 py-1 text-sm"
          />
        ) : (
          formatDateTimeRu(match.date_time)
        )}
      </td>
      <td className="px-3 py-2 text-sm">
        {canEditStatusAndDate ? (
          <select
            value={match.status}
            onChange={(e) => onChange?.({ status: e.target.value as MatchStatus })}
            className="border border-gray-300 rounded px-2 py-1 text-sm"
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
