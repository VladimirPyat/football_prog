import type { MatchOut, PredictionEntryOut } from "@/types/api";

function outcome(score1: number, score2: number): "p1" | "x" | "p2" {
  if (score1 > score2) return "p1";
  if (score1 < score2) return "p2";
  return "x";
}

interface OutcomeStatsFooterProps {
  matches: MatchOut[];
  entries: PredictionEntryOut[];
}

export function OutcomeStatsFooter({ matches, entries }: OutcomeStatsFooterProps) {
  const stats = matches.map((m) => {
    let p1 = 0;
    let x = 0;
    let p2 = 0;
    for (const entry of entries) {
      const pred = entry.predictions?.find((p) => p.match_id === m.id);
      if (!pred || pred.score1 == null || pred.score2 == null) continue;
      const o = outcome(pred.score1, pred.score2);
      if (o === "p1") p1++;
      else if (o === "x") x++;
      else p2++;
    }
    return { matchId: m.id, p1, x, p2 };
  });

  return (
    <tr className="bg-gray-50 border-t-2 border-gray-200">
      <td className="px-3 py-2 font-medium text-gray-700 sticky left-0 bg-gray-50">Статистика</td>
      {stats.map((s) => (
        <td key={s.matchId} className="px-1 py-2 text-center text-sm min-w-[4.5rem]">
          <div className="text-green-600">П1: {s.p1}</div>
          <div className="text-gray-500">X: {s.x}</div>
          <div className="text-blue-600">П2: {s.p2}</div>
        </td>
      ))}
    </tr>
  );
}
