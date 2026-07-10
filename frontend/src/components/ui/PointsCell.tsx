import { COL_DIGIT2, COL_DIGIT3 } from "@/lib/table/columnStyles";

type DigitClass = typeof COL_DIGIT2 | typeof COL_DIGIT3 | string;

export interface PointsCellProps {
  value: number | string;
  highlight?: boolean;
  digitClass?: DigitClass;
  empty?: string;
}

export function PointsCell({
  value,
  highlight = false,
  digitClass = COL_DIGIT2,
  empty = "—",
}: PointsCellProps) {
  const display = value === null || value === undefined ? empty : value;
  const n = typeof value === "number" ? value : null;
  const isPositive = n != null && n > 0;

  return (
    <td
      className={`${digitClass} ${
        highlight ? "bg-green-50 font-bold text-green-700" : ""
      } ${isPositive && !highlight ? "text-green-600 font-medium" : "text-gray-700"}`}
    >
      {display}
    </td>
  );
}

export function MatchPointsCell({ points }: { points: number | null }) {
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

export function TotalCell({
  value,
  highlight,
}: {
  value: number | string;
  highlight?: boolean;
}) {
  return (
    <td
      className={`${COL_DIGIT3} ${
        highlight ? "bg-green-50 font-bold text-green-700" : "text-gray-700"
      }`}
    >
      {value}
    </td>
  );
}
