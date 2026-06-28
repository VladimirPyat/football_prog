"use client";

import { matchStatusLabel, roundStatusHint, roundStatusLabel } from "@/lib/admin/format";
import { effectiveRoundStatus, isDeadlinePassedNow } from "@/lib/admin/roundEffectiveStatus";
import type { ContestOut, MatchOut, RoundOut } from "@/types/api";

interface RoundStatusSidebarProps {
  contest: ContestOut;
  round: RoundOut;
  matches: MatchOut[];
  deadlinePassed: boolean;
}

const STATUS_BADGE: Record<string, string> = {
  DRAFT: "bg-gray-100 text-gray-800",
  ACTIVE: "bg-green-100 text-green-800",
  CLOSED: "bg-orange-100 text-orange-800",
  CALCULATED: "bg-blue-100 text-blue-800",
  PUBLISHED: "bg-purple-100 text-purple-800",
};

const POST_DEADLINE_HINT =
  "Дедлайн прогнозов прошёл. Прогнозы закрыты; ввод результатов — на вкладке «Результаты».";

export function RoundStatusSidebar({
  contest,
  round,
  matches,
  deadlinePassed,
}: RoundStatusSidebarProps) {
  const passed = deadlinePassed || isDeadlinePassedNow(round.deadline);
  const displayStatus = effectiveRoundStatus(round, passed);
  const badgeClass = STATUS_BADGE[displayStatus] ?? "bg-gray-100 text-gray-800";
  const hint = roundStatusHint(displayStatus);

  const activeHint =
    displayStatus === "ACTIVE"
      ? "Тур активен. Состав фиксирован; до начала матча — перенос времени, отмена или свободный тур."
      : displayStatus === "CLOSED" && round.status === "ACTIVE" && passed
        ? POST_DEADLINE_HINT
        : hint;

  return (
    <aside className="border border-gray-200 rounded-lg p-4 space-y-4 h-fit">
      <h3 className="text-sm font-semibold text-gray-900">Статус тура</h3>
      <div>
        <span className={`inline-block text-xs font-semibold px-2 py-1 rounded ${badgeClass}`}>
          {roundStatusLabel(displayStatus)}
        </span>
      </div>

      {activeHint && (
        <p className="text-xs text-blue-800 bg-blue-50 border border-blue-200 rounded px-3 py-2">
          {activeHint}
        </p>
      )}

      <dl className="space-y-2 text-sm">
        <div className="flex justify-between gap-2">
          <dt className="text-gray-500">Команд</dt>
          <dd className="font-medium">{contest.total_teams}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-gray-500">Макс. матчей</dt>
          <dd className="font-medium">{contest.matches_per_round}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-gray-500">Матчей в туре</dt>
          <dd className="font-medium">
            {matches.length} / {contest.matches_per_round}
          </dd>
        </div>
      </dl>

      {matches.length > 0 && round.status !== "DRAFT" && (
        <div className="pt-2 border-t border-gray-100">
          <p className="text-xs text-gray-500 mb-1">Статусы матчей</p>
          <ul className="text-xs space-y-1 max-h-32 overflow-y-auto">
            {matches.slice(0, 4).map((m) => (
              <li key={m.id} className="truncate">
                {m.team1} — {m.team2}: {matchStatusLabel(m.status)}
              </li>
            ))}
          </ul>
        </div>
      )}
    </aside>
  );
}
