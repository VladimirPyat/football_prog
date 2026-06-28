const TWENTY_FOUR_HOURS = 24 * 60 * 60;

/** Show amber warning when deadline is within 24 hours but not yet passed. */
export function shouldShowDeadlineWarning(secondsLeft: number): boolean {
  return secondsLeft > 0 && secondsLeft <= TWENTY_FOUR_HOURS;
}
