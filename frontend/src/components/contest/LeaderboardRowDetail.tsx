import type { LeaderboardTableRow } from "@/lib/leaderboard/mapLeaderboardRow";

interface LeaderboardRowDetailProps {
  row: LeaderboardTableRow;
}

const FIELDS: { key: keyof LeaderboardTableRow; label: string }[] = [
  { key: "rank", label: "Место" },
  { key: "predictions_count", label: "Дано прогнозов" },
  { key: "count_exact_high", label: "Точный кр. счёт" },
  { key: "count_exact", label: "Точный счёт" },
  { key: "count_diff", label: "Разница" },
  { key: "count_outcome", label: "Исход" },
  { key: "bonus1", label: "Бонус 1" },
  { key: "bonus2", label: "Бонус 2" },
  { key: "bonus3", label: "Бонус 3" },
  { key: "points_base", label: "Всего очков (без бонусов)" },
  { key: "total_bonus_points", label: "Всего бонусных очков" },
];

export function LeaderboardRowDetail({ row }: LeaderboardRowDetailProps) {
  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
      {FIELDS.map(({ key, label }) => (
        <div key={key} className="contents">
          <dt className="text-gray-500">{label}</dt>
          <dd className="text-gray-900 font-medium tabular-nums text-right">{row[key]}</dd>
        </div>
      ))}
      <div className="contents">
        <dt className="text-gray-500 font-medium">ИТОГО очков</dt>
        <dd className="text-green-700 font-bold tabular-nums text-right">
          {row.total_with_bonus3}
        </dd>
      </div>
    </dl>
  );
}
