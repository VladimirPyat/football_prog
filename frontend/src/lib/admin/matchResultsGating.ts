const TERMINAL_NO_SCORE = new Set(["VOID", "CANCELED"]);

/** True when supervisor may enter/edit score for this match on Результаты. */
export function canEnterMatchResult(
  match: { status: string; date_time: string },
  round: { status: string },
  now: Date = new Date(),
): boolean {
  const { status: roundStatus } = round;
  const { status: matchStatus, date_time: dateTime } = match;

  if (roundStatus === "CLOSED") {
    if (TERMINAL_NO_SCORE.has(matchStatus)) return false;
    const kickoff = Date.parse(dateTime);
    if (Number.isNaN(kickoff)) return false;
    return now.getTime() >= kickoff;
  }

  if (roundStatus === "CALCULATED") {
    return matchStatus === "FINISHED";
  }

  return false;
}

/** True when at least one match in round has started (kickoff passed). */
export function roundHasStartedMatches(
  matches: { date_time: string }[],
  now: Date = new Date(),
): boolean {
  const nowMs = now.getTime();
  return matches.some((m) => {
    const kickoff = Date.parse(m.date_time);
    return !Number.isNaN(kickoff) && kickoff <= nowMs;
  });
}
