"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api/client";
import { contestAdmin } from "@/lib/api/endpoints";

interface LeaderboardRow {
  rank: number;
  user_name: string;
  total_with_bonus3: number;
}

interface RoundLeaderboardPreviewProps {
  contestId: number;
  roundId: number;
}

/**
 * Admin-only preview of the round leaderboard for CALCULATED rounds (§9.5).
 * Not shown on public contest pages.
 */
export function RoundLeaderboardPreview({ contestId, roundId }: RoundLeaderboardPreviewProps) {
  const [rows, setRows] = useState<LeaderboardRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    apiGet<{ leaderboard: LeaderboardRow[] }>(contestAdmin.rounds.leaderboard(contestId, roundId))
      .then((data) => setRows(data.leaderboard))
      .catch(() => setError("Не удалось загрузить таблицу"))
      .finally(() => setLoading(false));
  }, [contestId, roundId]);

  if (loading) return <p className="text-xs text-gray-500 animate-pulse">Загрузка таблицы…</p>;
  if (error) return <p className="text-xs text-red-600">{error}</p>;
  if (!rows.length)
    return <p className="text-xs text-gray-500">Очки не рассчитаны или участники отсутствуют.</p>;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <h4 className="text-sm font-semibold text-gray-900">Таблица тура</h4>
        <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
          Предпросмотр — тур ещё не опубликован
        </span>
      </div>
      <div className="overflow-x-auto border border-gray-200 rounded-lg">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left text-xs text-gray-500">#</th>
              <th className="px-3 py-2 text-left text-xs text-gray-500">Участник</th>
              <th className="px-3 py-2 text-right text-xs text-gray-500">Очки</th>
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, 10).map((r) => (
              <tr key={r.rank} className="border-t border-gray-100">
                <td className="px-3 py-1.5 text-gray-500">{r.rank}</td>
                <td className="px-3 py-1.5">{r.user_name}</td>
                <td className="px-3 py-1.5 text-right font-medium">{r.total_with_bonus3}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
