import { useCallback, useEffect, useState } from "react";
import {
  getStoredRoundId,
  resolveRoundId,
  setStoredRoundId,
  type RoundSelectionScope,
} from "@/lib/contest/roundSelectionStorage";

interface UsePersistedRoundSelectionOptions<TRound extends { id: number }> {
  contestId: number;
  scope: RoundSelectionScope;
  rounds: TRound[];
  pickDefault: () => number | null;
  /** Override stored value on first resolve (e.g. URL `?round=`). Consumed once. */
  initialRoundId?: number | null;
}

export function usePersistedRoundSelection<TRound extends { id: number }>({
  contestId,
  scope,
  rounds,
  pickDefault,
  initialRoundId = null,
}: UsePersistedRoundSelectionOptions<TRound>) {
  const [selectedRoundId, setSelectedRoundIdState] = useState<number | null>(null);
  const [initialConsumed, setInitialConsumed] = useState(false);

  useEffect(() => {
    if (rounds.length === 0) {
      setSelectedRoundIdState(null);
      return;
    }

    let stored = getStoredRoundId(contestId, scope);

    if (!initialConsumed && initialRoundId != null && rounds.some((r) => r.id === initialRoundId)) {
      stored = initialRoundId;
      setInitialConsumed(true);
      setStoredRoundId(contestId, scope, initialRoundId);
    }

    const resolved = resolveRoundId(rounds, stored, pickDefault);
    setSelectedRoundIdState((prev) => (prev === resolved ? prev : resolved));
  }, [contestId, scope, rounds, pickDefault, initialRoundId, initialConsumed]);

  const setSelectedRoundId = useCallback(
    (roundId: number) => {
      if (!rounds.some((r) => r.id === roundId)) return;
      setStoredRoundId(contestId, scope, roundId);
      setSelectedRoundIdState(roundId);
    },
    [contestId, scope, rounds],
  );

  return { selectedRoundId, setSelectedRoundId };
}
