import { apiGet } from "@/lib/api/client";
import { contestAdmin } from "@/lib/api/endpoints";
import type { MatchOut, RoundOut } from "@/types/api";

export interface PostponedMatchItem extends MatchOut {
  roundId: number;
  roundNumber: number;
}

export async function collectPostponedMatches(contestId: number): Promise<PostponedMatchItem[]> {
  const rounds = await apiGet<RoundOut[]>(contestAdmin.rounds.list(contestId));
  const postponed: PostponedMatchItem[] = [];

  for (const round of rounds) {
    const view = await apiGet<{ matches: MatchOut[] }>(
      contestAdmin.rounds.predictions(contestId, round.id),
    );
    for (const match of view.matches) {
      if (match.status === "POSTPONED") {
        postponed.push({
          ...match,
          roundId: round.id,
          roundNumber: round.number,
        });
      }
    }
  }

  return postponed;
}
