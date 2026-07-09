/**
 * Shorten a single team label for compact table column headers.
 */
export function shortenTeamLabel(name: string, maxLen = 4): string {
  const trimmed = name.trim();
  if (trimmed.length <= maxLen) return trimmed;

  const firstWord = trimmed.split(/[\s-]+/)[0] ?? trimmed;
  if (firstWord.length <= maxLen) return firstWord;

  return firstWord.slice(0, maxLen);
}

/** Compact "team1-team2" header for prediction/results matrices. */
export function formatTeamPairShort(team1: string, team2: string): string {
  return `${shortenTeamLabel(team1)}-${shortenTeamLabel(team2)}`;
}

/** Prefer configured short name; fall back to heuristic truncation. */
export function displayTeamShort(fullName: string, shortName?: string, maxLen = 4): string {
  if (shortName?.trim()) return shortName.trim();
  return shortenTeamLabel(fullName, maxLen);
}

export interface StackedTeamLabels {
  home: string;
  away: string;
}

/** Stacked home/away labels for narrow matrix columns. */
export function formatTeamPairStacked(
  team1: string,
  team2: string,
  team1Short?: string,
  team2Short?: string,
): StackedTeamLabels {
  return {
    home: displayTeamShort(team1, team1Short, 3),
    away: displayTeamShort(team2, team2Short, 3),
  };
}
