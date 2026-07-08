"use client";

import { useEffect, useState } from "react";
import { LeaderboardRowDetail } from "@/components/contest/LeaderboardRowDetail";
import { DetailModal } from "@/components/ui/DetailModal";
import type { LeaderboardTableRow } from "@/lib/leaderboard/mapLeaderboardRow";
import { COL_DIGIT2, COL_DIGIT3, COL_NAME, COL_RANK } from "@/lib/table/columnStyles";

const DESKTOP_BP = 1024;

const TH_BASE =
  "px-1 py-2 text-sm font-medium text-gray-700 border-b align-middle text-center";
const TH_STICKY = `${TH_BASE} sticky bg-gray-50 z-10`;
const TH_GROUP = `${TH_BASE} bg-gray-50`;
const TH_BONUS = `${TH_BASE} bg-amber-50/80`;
const TH_TOTAL = `${TH_BASE} bg-green-50`;

interface LeaderboardTableProps {
  rows: LeaderboardTableRow[];
  showCountColumns?: boolean;
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

function headerLabel(lines: string[]) {
  return (
    <span className="block leading-snug">
      {lines.map((line) => (
        <span key={line} className="block">
          {line}
        </span>
      ))}
    </span>
  );
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
      <div
        className="bg-white border border-gray-200 rounded-lg overflow-x-auto"
        data-testid="leaderboard-table"
      >
        <table className="border-collapse text-sm w-max max-w-full">
          <thead>
            {!compact && showCountColumns ? (
              <>
                <tr className="bg-gray-50">
                  <th rowSpan={2} className={`${TH_STICKY} left-0 ${COL_RANK}`}>
                    {headerLabel(["Место"])}
                  </th>
                  <th
                    rowSpan={2}
                    className={`${TH_STICKY} left-8 ${COL_NAME} max-w-[9rem] text-left`}
                  >
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
                  <th rowSpan={2} className={`${TH_GROUP} ${COL_DIGIT3}`}>
                    {headerLabel(["Всего очков", "(без бонусов)"])}
                  </th>
                  <th rowSpan={2} className={`${TH_GROUP} ${COL_DIGIT3}`}>
                    {headerLabel(["Всего", "бонусных", "очков"])}
                  </th>
                  <th rowSpan={2} className={`${TH_TOTAL} ${COL_DIGIT3}`}>
                    {headerLabel(["ИТОГО", "очков"])}
                  </th>
                </tr>
                <tr className="bg-gray-50">
                  <th className={`${TH_GROUP} ${COL_DIGIT2}`}>{headerLabel(["крупный"])}</th>
                  <th className={`${TH_GROUP} ${COL_DIGIT2}`}>{headerLabel(["счёт"])}</th>
                  <th className={`${TH_BONUS} ${COL_DIGIT2}`}>1</th>
                  <th className={`${TH_BONUS} ${COL_DIGIT2}`}>2</th>
                  <th className={`${TH_BONUS} ${COL_DIGIT2}`}>3</th>
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
                <th className={`${TH_GROUP} ${COL_DIGIT3}`}>
                  {headerLabel(["Всего очков", "(без бонусов)"])}
                </th>
                <th className={`${TH_GROUP} ${COL_DIGIT3}`}>
                  {headerLabel(["Всего", "бонусных", "очков"])}
                </th>
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
                  className={`${COL_NAME} font-medium text-gray-900 sticky left-8 bg-white text-sm leading-snug`}
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
                    <td className={`${COL_DIGIT2} bg-amber-50/50`}>{row.bonus1}</td>
                    <td className={`${COL_DIGIT2} bg-amber-50/50`}>{row.bonus2}</td>
                    <td className={`${COL_DIGIT2} bg-amber-50/50`}>{row.bonus3}</td>
                  </>
                )}
                <PointsCell value={row.points_base} digitClass={COL_DIGIT3} />
                <PointsCell value={row.total_bonus_points} digitClass={COL_DIGIT3} />
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
