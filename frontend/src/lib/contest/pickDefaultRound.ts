import type { PublicTab } from "@/components/contest/PublicTabs";
import { isRoundPubliclyVisible } from "@/lib/contest/roundPublicVisibility";
import type { RoundOut } from "@/types/api";

/** Default round for public contest page when nothing is stored. */
export function pickDefaultRound(rounds: RoundOut[], tab: PublicTab): number | null {
  if (rounds.length === 0) return null;

  if (tab === "predictions") {
    const active = rounds.find((r) => r.status === "ACTIVE");
    if (active) return active.id;
    const past = [...rounds].reverse().find((r) => r.status !== "DRAFT");
    return past?.id ?? rounds[rounds.length - 1].id;
  }

  const published = [...rounds].reverse().find((r) => isRoundPubliclyVisible(r.status));
  return published?.id ?? rounds[rounds.length - 1].id;
}

/** Default for predict entry page — prefer ACTIVE, else last non-DRAFT. */
export function pickDefaultPredictRound(rounds: RoundOut[]): number | null {
  if (rounds.length === 0) return null;
  const active = rounds.find((r) => r.status === "ACTIVE");
  if (active) return active.id;
  const past = [...rounds].reverse().find((r) => r.status !== "DRAFT");
  return past?.id ?? rounds[rounds.length - 1].id;
}

/** Admin rounds page — latest round in list. */
export function pickDefaultAdminRound(rounds: RoundOut[]): number | null {
  if (rounds.length === 0) return null;
  return rounds[rounds.length - 1].id;
}
