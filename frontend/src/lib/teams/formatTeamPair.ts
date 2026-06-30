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

export interface StackedTeamLabels {
  home: string;
  away: string;
}

/** Stacked home/away labels for narrow matrix columns. */
export function formatTeamPairStacked(team1: string, team2: string): StackedTeamLabels {
  return {
    home: shortenTeamLabel(team1, 3),
    away: shortenTeamLabel(team2, 3),
  };
}
