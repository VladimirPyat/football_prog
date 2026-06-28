import { apiGet, AppError } from "@/lib/api/client";
import { contests as contestEndpoints, me } from "@/lib/api/endpoints";
import type { ContestOut, PublicContestOut, UserContestOut } from "@/types/api";

/** Fallback rules when participant cannot read full contest (GET /contests/{id} is SUPERVISOR+). */
const PARTICIPANT_RULES_FALLBACK: Record<string, unknown> = {
  constraints: { score_validation_range: [0, 20] },
};

function buildParticipantContestShell(
  base: Pick<ContestOut, "id" | "name" | "status">,
): ContestOut {
  return {
    id: base.id,
    name: base.name,
    status: base.status,
    slug: null,
    is_locked: true,
    paused_at: null,
    finished_at: null,
    total_teams: 16,
    matches_per_round: 8,
    total_rounds: 10,
    is_round_robin: true,
    rules_json: PARTICIPANT_RULES_FALLBACK,
  };
}

/** Staff: full contest. Participants / visitors: shell from /me/contests or /contests/public. */
export async function fetchContestDetails(contestId: number): Promise<ContestOut | null> {
  try {
    return await apiGet<ContestOut>(contestEndpoints.byId(contestId));
  } catch (e) {
    if (!(e instanceof AppError) || (e.status !== 403 && e.status !== 401)) {
      throw e;
    }
  }

  try {
    const enrolled = await apiGet<UserContestOut[]>(me.contests());
    const mine = enrolled.find((c) => c.id === contestId);
    if (mine) {
      return buildParticipantContestShell({
        id: mine.id,
        name: mine.name,
        status: mine.status,
      });
    }
  } catch {
    // fall through to public list
  }

  const publicList = await apiGet<PublicContestOut[]>(contestEndpoints.public(), false);
  const pub = publicList.find((c) => c.id === contestId);
  return pub
    ? buildParticipantContestShell({ id: pub.id, name: pub.name, status: pub.status })
    : null;
}
