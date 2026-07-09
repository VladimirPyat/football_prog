"use client";

import { formatTeamPairStacked } from "@/lib/teams/formatTeamPair";

interface TeamColumnHeaderProps {
  team1: string;
  team2: string;
  team1Short?: string;
  team2Short?: string;
  size?: "compact" | "normal";
}

export function TeamColumnHeader({
  team1,
  team2,
  team1Short,
  team2Short,
  size = "compact",
}: TeamColumnHeaderProps) {
  const { home, away } = formatTeamPairStacked(team1, team2, team1Short, team2Short);
  const textClass = size === "normal" ? "text-sm" : "text-[10px]";

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
