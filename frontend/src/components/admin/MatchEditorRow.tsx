"use client";

import { formatDateTimeRu, fromDatetimeLocal, toDatetimeLocal } from "@/lib/admin/format";
import type { MatchOut, MatchStatus } from "@/types/api";

interface MatchEditorRowProps {
  match: MatchOut;
  canEditStructure: boolean;
  canEditStatusAndDate: boolean;
  teams?: { id: number; name: string }[];
  onChange?: (patch: { date_time?: string; status?: MatchStatus }) => void;
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
  onChange,
}: MatchEditorRowProps) {
  return (
    <tr className="border-t border-gray-200">
      <td className="px-3 py-2 text-sm">
        {match.team1} — {match.team2}
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
          match.status
        )}
      </td>
      {!canEditStructure && !canEditStatusAndDate && (
        <td className="px-3 py-2 text-sm text-gray-400">Только просмотр</td>
      )}
    </tr>
  );
}
