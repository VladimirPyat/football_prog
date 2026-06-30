"use client";

import { formatTeamPairStacked } from "@/lib/teams/formatTeamPair";

interface TeamColumnHeaderProps {
  team1: string;
  team2: string;
  size?: "compact" | "normal";
}

export function TeamColumnHeader({ team1, team2, size = "compact" }: TeamColumnHeaderProps) {
  const { home, away } = formatTeamPairStacked(team1, team2);
  const textClass = size === "normal" ? "text-xs" : "text-[10px]";

  return (
    <div
      className={`flex flex-col items-center leading-tight gap-0.5 ${textClass}`}
      title={`${team1} — ${team2}`}
    >
      <span className="font-medium text-gray-800">{home}</span>
      <span className="text-gray-500">{away}</span>
    </div>
  );
}
