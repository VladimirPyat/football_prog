"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "@/lib/api/client";
import { contestAdmin } from "@/lib/api/endpoints";
import type { RoundPredictionsView } from "@/types/api";

export function useRoundMatches(contestId: number, roundId: number | null) {
  const [view, setView] = useState<RoundPredictionsView | null>(null);
  const [loading, setLoading] = useState(false);

  const refetch = useCallback(async () => {
    if (!roundId) {
      setView(null);
      return;
    }
    setLoading(true);
    try {
      const data = await apiGet<RoundPredictionsView>(
        contestAdmin.rounds.predictions(contestId, roundId),
      );
      setView(data);
    } finally {
      setLoading(false);
    }
  }, [contestId, roundId]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return { view, matches: view?.matches ?? [], deadlinePassed: view?.deadline_passed ?? false, loading, refetch };
}
