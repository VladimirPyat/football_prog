import type { RoundOut, UserRole } from "@/types/api";

const PRIVILEGED_ROLES = new Set<UserRole>(["SUPPORT", "SUPERVISOR"]);

/** Hide DRAFT rounds from participants and visitors; staff see all rounds. */
export function filterParticipantVisibleRounds(
  rounds: RoundOut[],
  viewerRole?: UserRole | null,
): RoundOut[] {
  if (viewerRole && PRIVILEGED_ROLES.has(viewerRole)) {
    return rounds;
  }
  return rounds.filter((r) => r.status !== "DRAFT");
}
