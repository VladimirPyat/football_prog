"use client";

import { useEffect, useState } from "react";
import { LeaderboardRowDetail } from "@/components/contest/LeaderboardRowDetail";
import { MultiLineColumnHeader } from "@/components/contest/MultiLineColumnHeader";
import { DetailModal } from "@/components/ui/DetailModal";
import type { MockLeaderboardRow } from "@/lib/mocks/contestDisplayMock";
import {
  adaptiveNameClass,
  COL_DIGIT2,
  COL_DIGIT3,
  COL_NAME,
  COL_RANK,
} from "@/lib/table/columnStyles";

const DESKTOP_BP = 1024;

interface LeaderboardTableProps {
  rows: MockLeaderboardRow[];
}

function PointsCell({
  value,
  highlight,
  digitClass = COL_DIGIT2,
}: {
  value: number | string;
  highlight?: boolean;
  digitClass?: string;
}) {
  const n = typeof value === "number" ? value : null;
  const isPositive = n != null && n > 0;
  return (
    <td
      className={`${digitClass} ${
        highlight ? "bg-green-50 font-bold text-green-700" : ""
      } ${isPositive && !highlight ? "text-green-600 font-medium" : "text-gray-700"}`}
    >
      {value}
    </td>
  );
}

export function LeaderboardTable({ rows }: LeaderboardTableProps) {
  const [compact, setCompact] = useState(false);
  const [selectedRow, setSelectedRow] = useState<MockLeaderboardRow | null>(null);

  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${DESKTOP_BP - 1}px)`);
    const update = () => setCompact(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);

  const handleRowClick = (row: MockLeaderboardRow) => {
    if (compact) setSelectedRow(row);
  };

  return (
    <>
      <div className="bg-white border border-gray-200 rounded-lg overflow-x-auto" data-testid="leaderboard-table">
        <table className="border-collapse text-sm w-max max-w-full">
          <thead>
            <tr className="bg-gray-50">
              <th className={`${COL_RANK} font-medium text-gray-700 border-b sticky left-0 bg-gray-50 z-10`}>
                <MultiLineColumnHeader label="Место" />
              </th>
              <th
                className={`${COL_NAME} font-medium text-gray-700 border-b sticky left-8 bg-gray-50 z-10 max-w-[8.5rem]`}
              >
                <MultiLineColumnHeader label="Фамилия Имя" />
              </th>
              {!compact && (
                <>
                  <th className={`${COL_DIGIT2} font-medium border-b`}>
                    <MultiLineColumnHeader label="Дано прогнозов" />
                  </th>
                  <th className={`${COL_DIGIT2} font-medium border-b`}>
                    <MultiLineColumnHeader label="Точный кр. счет" />
                  </th>
                  <th className={`${COL_DIGIT2} font-medium border-b`}>
                    <MultiLineColumnHeader label="Точный счет" />
                  </th>
                  <th className={`${COL_DIGIT2} font-medium border-b`}>
                    <MultiLineColumnHeader label="Разница" />
                  </th>
                  <th className={`${COL_DIGIT2} font-medium border-b`}>
                    <MultiLineColumnHeader label="Исход" />
                  </th>
                  <th className={`${COL_DIGIT2} font-medium border-b bg-amber-50/80`}>
                    <MultiLineColumnHeader label="Бонус 1" />
                  </th>
                  <th className={`${COL_DIGIT2} font-medium border-b bg-amber-50/80`}>
                    <MultiLineColumnHeader label="Бонус 2" />
                  </th>
                  <th className={`${COL_DIGIT2} font-medium border-b bg-amber-50/80`}>
                    <MultiLineColumnHeader label="Бонус 3" />
                  </th>
                </>
              )}
              <th className={`${COL_DIGIT3} font-medium border-b`}>
                <MultiLineColumnHeader label="Очки без бонуса" />
              </th>
              <th className={`${COL_DIGIT3} font-medium border-b`}>
                <MultiLineColumnHeader label="Очки с бонусами" />
              </th>
              <th className={`${COL_DIGIT3} font-medium border-b bg-green-50`}>
                <MultiLineColumnHeader label="Всего очков" />
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.rank}
                className={`border-b border-gray-100 hover:bg-gray-50/50 ${
                  compact ? "cursor-pointer active:bg-gray-100" : ""
                }`}
                onClick={() => handleRowClick(row)}
                onKeyDown={(e) => {
                  if (compact && (e.key === "Enter" || e.key === " ")) {
                    e.preventDefault();
                    handleRowClick(row);
                  }
                }}
                tabIndex={compact ? 0 : undefined}
                role={compact ? "button" : undefined}
              >
                <td className={`${COL_RANK} text-gray-600 sticky left-0 bg-white`}>{row.rank}</td>
                <td
                  className={`${COL_NAME} font-medium text-gray-900 sticky left-8 bg-white ${adaptiveNameClass(row.user_name)}`}
                >
                  {row.user_name}
                </td>
                {!compact && (
                  <>
                    <PointsCell value={row.predictions_count} />
                    <PointsCell value={row.count_exact_high} />
                    <PointsCell value={row.count_exact} />
                    <PointsCell value={row.count_diff} />
                    <PointsCell value={row.count_outcome} />
                    <td className={`${COL_DIGIT2} bg-amber-50/50`}>{row.bonus1}</td>
                    <td className={`${COL_DIGIT2} bg-amber-50/50`}>{row.bonus2}</td>
                    <td className={`${COL_DIGIT2} bg-amber-50/50`}>{row.bonus3}</td>
                  </>
                )}
                <PointsCell value={row.total_without_bonus3} digitClass={COL_DIGIT3} />
                <PointsCell value={row.total_with_bonus3} digitClass={COL_DIGIT3} />
                <PointsCell value={row.total_with_bonus3} highlight digitClass={COL_DIGIT3} />
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <DetailModal
        open={selectedRow != null}
        onClose={() => setSelectedRow(null)}
        title={selectedRow ? `${selectedRow.user_name} — место ${selectedRow.rank}` : ""}
      >
        {selectedRow && <LeaderboardRowDetail row={selectedRow} />}
      </DetailModal>
    </>
  );
}
