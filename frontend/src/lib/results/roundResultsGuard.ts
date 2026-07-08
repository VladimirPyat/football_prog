import type { RoundStatus } from "@/types/api";
import { isRoundPubliclyVisible } from "@/lib/contest/roundPublicVisibility";

/** Public results/leaderboard fetch is allowed only for PUBLISHED rounds. */
export function shouldFetchPublicResults(status: RoundStatus): boolean {
  return isRoundPubliclyVisible(status);
}
