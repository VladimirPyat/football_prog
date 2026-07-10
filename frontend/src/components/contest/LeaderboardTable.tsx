"use client";

import { useEffect, useState } from "react";
import { LeaderboardRowDetail } from "@/components/contest/LeaderboardRowDetail";
import { DataTable } from "@/components/ui/DataTable";
import { DetailModal } from "@/components/ui/DetailModal";
import { PointsCell } from "@/components/ui/PointsCell";
import type { LeaderboardTableRow } from "@/lib/leaderboard/mapLeaderboardRow";
import { COL_DIGIT2, COL_DIGIT3, COL_NAME, COL_RANK } from "@/lib/table/columnStyles";
import { headerLabel } from "@/lib/table/headerLabel";
import { TH_BONUS, TH_GROUP, TH_STICKY, TH_TOTAL } from "@/lib/table/tableHeaderStyles";

const DESKTOP_BP = 1024;

interface LeaderboardTableProps {
  rows: LeaderboardTableRow[];
  showCountColumns?: boolean;
}

export function LeaderboardTable({ rows, showCountColumns = true }: LeaderboardTableProps) {
  const [compact, setCompact] = useState(false);
  const [selectedRow, setSelectedRow] = useState<LeaderboardTableRow | null>(null);

  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${DESKTOP_BP - 1}px)`);
    const update = () => setCompact(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);

  const handleRowClick = (row: LeaderboardTableRow) => {
    if (compact) setSelectedRow(row);
  };

  return (
    <>
      <DataTable testId="leaderboard-table">
        <thead>
          {!compact && showCountColumns ? (
            <>
              <tr className="bg-gray-50">
                <th rowSpan={2} className={`${TH_STICKY} left-0 ${COL_RANK}`}>
                  {headerLabel(["Место"])}
                </th>
                <th rowSpan={2} className={`${TH_STICKY} left-8 ${COL_NAME} text-left`}>
                  {headerLabel(["Фамилия", "Имя"])}
                </th>
                <th rowSpan={2} className={`${TH_GROUP} ${COL_DIGIT3}`}>
                  {headerLabel(["Дано", "прогнозов"])}
                </th>
                <th colSpan={2} className={TH_GROUP}>
                  {headerLabel(["Точный счёт"])}
                </th>
                <th rowSpan={2} className={`${TH_GROUP} ${COL_DIGIT2}`}>
                  {headerLabel(["Разница"])}
                </th>
                <th rowSpan={2} className={`${TH_GROUP} ${COL_DIGIT2}`}>
                  {headerLabel(["Исход"])}
                </th>
                <th colSpan={3} className={TH_BONUS}>
                  {headerLabel(["Бонус"])}
                </th>
                <th colSpan={2} className={TH_GROUP}>
                  {headerLabel(["Сумма очков"])}
                </th>
                <th rowSpan={2} className={`${TH_TOTAL} ${COL_DIGIT3}`}>
                  {headerLabel(["ИТОГО", "очков"])}
                </th>
              </tr>
              <tr className="bg-gray-50">
                <th className={`${TH_GROUP} ${COL_DIGIT2}`}>{headerLabel(["крупный"])}</th>
                <th className={`${TH_GROUP} ${COL_DIGIT2}`}>—</th>
                <th className={`${TH_BONUS} ${COL_DIGIT2}`}>1</th>
                <th className={`${TH_BONUS} ${COL_DIGIT2}`}>2</th>
                <th className={`${TH_BONUS} ${COL_DIGIT2}`}>3</th>
                <th className={`${TH_GROUP} ${COL_DIGIT3}`}>{headerLabel(["без бонусов"])}</th>
                <th className={`${TH_GROUP} ${COL_DIGIT3}`}>{headerLabel(["бонусы"])}</th>
              </tr>
            </>
          ) : (
            <tr className="bg-gray-50">
              <th className={`${TH_STICKY} left-0 ${COL_RANK}`}>{headerLabel(["Место"])}</th>
              <th className={`${TH_STICKY} left-8 ${COL_NAME} text-left`}>
                {headerLabel(["Фамилия", "Имя"])}
              </th>
              {!compact && (
                <>
                  <th className={`${TH_GROUP} ${COL_DIGIT3}`}>
                    {headerLabel(["Дано", "прогнозов"])}
                  </th>
                  <th className={`${TH_BONUS} ${COL_DIGIT2}`}>{headerLabel(["Бонус", "1"])}</th>
                  <th className={`${TH_BONUS} ${COL_DIGIT2}`}>{headerLabel(["Бонус", "2"])}</th>
                  <th className={`${TH_BONUS} ${COL_DIGIT2}`}>{headerLabel(["Бонус", "3"])}</th>
                </>
              )}
              <th className={`${TH_GROUP} ${COL_DIGIT3}`}>{headerLabel(["без бонусов"])}</th>
              <th className={`${TH_GROUP} ${COL_DIGIT3}`}>{headerLabel(["бонусы"])}</th>
              <th className={`${TH_TOTAL} ${COL_DIGIT3}`}>{headerLabel(["ИТОГО", "очков"])}</th>
            </tr>
          )}
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
                className={`${COL_NAME} font-medium text-gray-900 sticky left-8 bg-white leading-snug`}
              >
                {row.user_name}
              </td>
              {!compact && (
                <>
                  <PointsCell value={row.predictions_count} digitClass={COL_DIGIT3} />
                  {showCountColumns && (
                    <>
                      <PointsCell value={row.count_exact_high} />
                      <PointsCell value={row.count_exact} />
                      <PointsCell value={row.count_diff} />
                      <PointsCell value={row.count_outcome} />
                    </>
                  )}
                  <td className={`${COL_DIGIT2} bg-amber-50/50 text-gray-700`}>{row.bonus1}</td>
                  <td className={`${COL_DIGIT2} bg-amber-50/50 text-gray-700`}>{row.bonus2}</td>
                  <td className={`${COL_DIGIT2} bg-amber-50/50 text-gray-700`}>{row.bonus3}</td>
                </>
              )}
              <PointsCell value={row.points_base} digitClass={COL_DIGIT3} />
              <PointsCell value={row.total_bonus_points} digitClass={COL_DIGIT3} />
              <PointsCell value={row.total_with_bonus3} highlight digitClass={COL_DIGIT3} />
            </tr>
          ))}
        </tbody>
      </DataTable>

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
