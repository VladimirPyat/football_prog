import type { MatchOut } from "@/types/api";

export function roundHasVisiblePostponements(matches: MatchOut[]): boolean {
  return matches.some((m) => m.status === "POSTPONED");
}

export const BONUSES_PENDING_FALLBACK_MESSAGE =
  "Бонусы тура будут рассчитаны после сыгранных перенесённых матчей. Основные очки по завершённым матчам уже учтены.";
