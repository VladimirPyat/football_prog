"use client";

import { useEffect, useState } from "react";
import { MultiLineColumnHeader } from "@/components/contest/MultiLineColumnHeader";
import { ResultsRowDetail } from "@/components/contest/ResultsRowDetail";
import { TeamColumnHeader } from "@/components/predictions/TeamColumnHeader";
import { DetailModal } from "@/components/ui/DetailModal";
import type { ResultsMatrixMatch, ResultsMatrixRow } from "@/lib/results/mapRoundResultsRow";
import { adaptiveNameClass, COL_DIGIT2, COL_DIGIT3, COL_NAME } from "@/lib/table/columnStyles";

const MOBILE_BP = 1024;

interface ResultsMatrixProps {
  matches: ResultsMatrixMatch[];
  rows: ResultsMatrixRow[];
  roundLabel: string;
}

function MatchPointsCell({ points }: { points: number | null }) {
  if (points == null) {
    return <td className={`${COL_DIGIT2} text-gray-400`}>—</td>;
  }
  const positive = points > 0;
  return (
    <td className={`${COL_DIGIT2} ${positive ? "text-green-600 font-medium" : "text-gray-400"}`}>
      {points}
    </td>
  );
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
      <div
        className="bg-white border border-gray-200 rounded-lg overflow-x-auto"
        data-testid="results-matrix"
      >
        <table className="border-collapse text-base w-max max-w-full">
          <thead>
            <tr className="bg-gray-50">
              <th className={`${COL_NAME} font-medium text-gray-700 border-b text-sm`}>
                <MultiLineColumnHeader label="Счет" />
              </th>
              {matches.map((m) => (
                <th
                  key={m.id}
                  className="px-0.5 py-1.5 text-center font-medium text-gray-700 border-b w-10 min-w-[2.5rem] max-w-[2.5rem]"
                >
                  <TeamColumnHeader team1={m.team1} team2={m.team2} size="normal" />
                </th>
              ))}
              {!compact && (
                <>
                  <th className={`${COL_DIGIT2} font-medium border-b bg-amber-50/80`}>
                    <MultiLineColumnHeader label="Бонус 1" />
                  </th>
                  <th className={`${COL_DIGIT2} font-medium border-b bg-amber-50/80`}>
                    <MultiLineColumnHeader label="Бонус 2" />
                  </th>
                  <th className={`${COL_DIGIT3} font-medium border-b`}>
                    <MultiLineColumnHeader label="Итого без бон." />
                  </th>
                  <th className={`${COL_DIGIT2} font-medium border-b bg-amber-50/80`}>
                    <MultiLineColumnHeader label="Бонус 3" />
                  </th>
                </>
              )}
              <th className={`${COL_DIGIT3} font-medium border-b bg-green-50`}>
                <MultiLineColumnHeader label="ИТОГО" />
              </th>
            </tr>
            <tr className="bg-gray-50 text-sm text-gray-500">
              <th className={`${COL_NAME} text-left border-b font-normal`}>{roundLabel}</th>
              {matches.map((m) => (
                <th
                  key={`score-${m.id}`}
                  className="px-0.5 py-1 text-center border-b font-normal tabular-nums"
                >
                  {m.score1 ?? "—"}:{m.score2 ?? "—"}
                </th>
              ))}
              {!compact && <th colSpan={4} className="border-b" />}
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
                  className={`${COL_NAME} font-medium text-gray-900 bg-white ${adaptiveNameClass(row.user_name)}`}
                >
                  {row.user_name}
                </td>
                {row.match_points.map((pts, i) => (
                  <MatchPointsCell key={`${row.user_name}-${i}`} points={pts} />
                ))}
                {!compact && (
                  <>
                    <td className={`${COL_DIGIT2} bg-amber-50/50 text-gray-600`}>
                      {row.bonus1 ?? "—"}
                    </td>
                    <td className={`${COL_DIGIT2} bg-amber-50/50 text-gray-600`}>
                      {row.bonus2 ?? "—"}
                    </td>
                    <td className={COL_DIGIT3}>{row.total_without_bonus}</td>
                    <td className={`${COL_DIGIT2} bg-amber-50/50 text-gray-600`}>
                      {row.bonus3 ?? "—"}
                    </td>
                  </>
                )}
                <td className={`${COL_DIGIT3} bg-green-50 text-green-700`}>{row.total}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

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
