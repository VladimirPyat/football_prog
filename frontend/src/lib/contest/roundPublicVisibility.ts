/**
 * Round public visibility rules (§9.9).
 *
 * Participants and visitors must not see a round's leaderboard or results
 * until the supervisor publishes the round.
 */

import type { RoundStatus } from "@/types/api";

/**
 * Returns true only when the round is PUBLISHED — i.e. the supervisor has
 * confirmed results and the data is safe to show publicly.
 */
export function isRoundPubliclyVisible(status: RoundStatus): boolean {
  return status === "PUBLISHED";
}

/** Copy shown on public contest pages for non-published rounds. */
export const ROUND_NOT_PUBLISHED_COPY =
  "Будет доступно после проверки организатором";

/** Secondary copy for round selector in public contest pages. */
export const ROUND_NOT_PUBLISHED_SECONDARY =
  "Организатор ещё не опубликовал результаты тура";
