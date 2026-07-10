"use client";

import { useEffect, useState } from "react";
import { ResultsRowDetail } from "@/components/contest/ResultsRowDetail";
import { TeamColumnHeader } from "@/components/predictions/TeamColumnHeader";
import { DataTable } from "@/components/ui/DataTable";
import { DetailModal } from "@/components/ui/DetailModal";
import { MatchPointsCell, TotalCell } from "@/components/ui/PointsCell";
import type { ResultsMatrixMatch, ResultsMatrixRow } from "@/lib/results/mapRoundResultsRow";
import { adaptiveNameClass, COL_DIGIT2, COL_DIGIT3, COL_NAME } from "@/lib/table/columnStyles";
import { headerLabel } from "@/lib/table/headerLabel";
import { TH_BONUS, TH_GROUP, TH_STICKY, TH_TOTAL } from "@/lib/table/tableHeaderStyles";

const MOBILE_BP = 1024;

interface ResultsMatrixProps {
  matches: ResultsMatrixMatch[];
  rows: ResultsMatrixRow[];
  roundLabel: string;
}

export function ResultsMatrix({ matches, rows, roundLabel }: ResultsMatrixProps) {
  const [compact, setCompact] = useState(false);
  const [selectedRow, setSelectedRow] = useState<ResultsMatrixRow | null>(null);

  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${MOBILE_BP - 1}px)`);
    const update = () => setCompact(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);

  const handleRowClick = (row: ResultsMatrixRow) => {
    if (compact) setSelectedRow(row);
  };

  return (
    <>
      <DataTable testId="results-matrix">
        <thead>
          <tr className="bg-gray-50">
            <th className={`${TH_STICKY} left-0 ${COL_NAME} text-left`}>
              {headerLabel(["Счёт"])}
            </th>
            {matches.map((m) => (
              <th
                key={m.id}
                className={`${TH_GROUP} w-[3.25rem] min-w-[3.25rem] max-w-[3.5rem] px-0.5 py-1.5`}
              >
                <TeamColumnHeader
                  team1={m.team1}
                  team2={m.team2}
                  team1Short={m.team1_short}
                  team2Short={m.team2_short}
                  size="normal"
                />
              </th>
            ))}
            {!compact && (
              <>
                <th className={`${TH_GROUP} ${COL_DIGIT2}`}>{headerLabel(["Исход"])}</th>
                <th className={`${TH_BONUS} ${COL_DIGIT2}`}>{headerLabel(["Бонус", "1"])}</th>
                <th className={`${TH_BONUS} ${COL_DIGIT2}`}>{headerLabel(["Бонус", "2"])}</th>
                <th className={`${TH_GROUP} ${COL_DIGIT3}`}>
                  {headerLabel(["Итого", "без бон."])}
                </th>
                <th className={`${TH_BONUS} ${COL_DIGIT2}`}>{headerLabel(["Бонус", "3"])}</th>
              </>
            )}
            <th className={`${TH_TOTAL} ${COL_DIGIT3}`}>{headerLabel(["ИТОГО"])}</th>
          </tr>
          <tr className="bg-gray-50 text-sm text-gray-500">
            <th className={`${TH_STICKY} left-0 ${COL_NAME} text-left border-b font-normal`}>
              {roundLabel}
            </th>
            {matches.map((m) => (
              <th
                key={`score-${m.id}`}
                className={`${COL_DIGIT2} border-b font-normal text-gray-500`}
              >
                {m.score1 ?? "—"}:{m.score2 ?? "—"}
              </th>
            ))}
            {!compact && <th colSpan={5} className="border-b" />}
            <th className="border-b" />
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.user_name}
              className={`border-b border-gray-100 ${
                compact ? "cursor-pointer active:bg-gray-100 hover:bg-gray-50/50" : ""
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
              <td
                className={`${COL_NAME} font-medium text-gray-900 bg-white sticky left-0 ${adaptiveNameClass(row.user_name)}`}
              >
                {row.user_name}
              </td>
              {row.match_points.map((pts, i) => (
                <MatchPointsCell key={`${row.user_name}-${i}`} points={pts} />
              ))}
              {!compact && (
                <>
                  <td className={`${COL_DIGIT2} text-gray-700`}>{row.correct_outcomes}</td>
                  <td className={`${COL_DIGIT2} bg-amber-50/50 text-gray-700`}>
                    {row.bonus1 ?? "—"}
                  </td>
                  <td className={`${COL_DIGIT2} bg-amber-50/50 text-gray-700`}>
                    {row.bonus2 ?? "—"}
                  </td>
                  <TotalCell value={row.total_without_bonus} />
                  <td className={`${COL_DIGIT2} bg-amber-50/50 text-gray-700`}>
                    {row.bonus3 ?? "—"}
                  </td>
                </>
              )}
              <TotalCell value={row.total} highlight />
            </tr>
          ))}
        </tbody>
      </DataTable>

      <DetailModal
        open={selectedRow != null}
        onClose={() => setSelectedRow(null)}
        title={selectedRow?.user_name ?? ""}
      >
        {selectedRow && <ResultsRowDetail row={selectedRow} matches={matches} />}
      </DetailModal>
    </>
  );
}
