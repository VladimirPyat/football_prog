import type { MockResultsMatch, MockResultsRow } from "@/lib/mocks/contestDisplayMock";

interface ResultsRowDetailProps {
  row: MockResultsRow;
  matches: MockResultsMatch[];
}

export function ResultsRowDetail({ row, matches }: ResultsRowDetailProps) {
  return (
    <div className="space-y-4 text-sm">
      <section>
        <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">Очки за матчи</h3>
        <ul className="space-y-1.5">
          {matches.map((m, i) => (
            <li key={m.id} className="flex justify-between gap-2">
              <span className="text-gray-700">
                {m.team1} — {m.team2}{" "}
                <span className="text-gray-400">
                  ({m.score1}:{m.score2})
                </span>
              </span>
              <span
                className={`tabular-nums font-medium shrink-0 ${
                  (row.match_points[i] ?? 0) > 0 ? "text-green-600" : "text-gray-400"
                }`}
              >
                {row.match_points[i] ?? "—"}
              </span>
            </li>
          ))}
        </ul>
      </section>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 border-t border-gray-100 pt-3">
        <dt className="text-gray-500">Бонус 1</dt>
        <dd className="text-right tabular-nums">{row.bonus1 ?? "—"}</dd>
        <dt className="text-gray-500">Бонус 2</dt>
        <dd className="text-right tabular-nums">{row.bonus2 ?? "—"}</dd>
        <dt className="text-gray-500">Итого без бон.</dt>
        <dd className="text-right tabular-nums">{row.total_without_bonus}</dd>
        <dt className="text-gray-500">Бонус 3</dt>
        <dd className="text-right tabular-nums">{row.bonus3 ?? "—"}</dd>
        <dt className="text-gray-700 font-medium">ИТОГО</dt>
        <dd className="text-right tabular-nums font-bold text-green-700">{row.total}</dd>
      </dl>
    </div>
  );
}
