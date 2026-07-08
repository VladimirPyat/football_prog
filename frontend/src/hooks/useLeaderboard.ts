"use client";

import { useCallback, useEffect, useState } from "react";
import { AppError, apiGet } from "@/lib/api/client";
import { contestPublic } from "@/lib/api/endpoints";
import type { LeaderboardOut } from "@/types/api";

export function useLeaderboard(contestId: number, roundId: number | null, enabled = true) {
  const [data, setData] = useState<LeaderboardOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notAvailable, setNotAvailable] = useState(false);

  const refetch = useCallback(async () => {
    if (!roundId || !enabled) {
      setData(null);
      setError(null);
      setNotAvailable(false);
      return;
    }
    setLoading(true);
    setError(null);
    setNotAvailable(false);
    try {
      const payload = await apiGet<LeaderboardOut>(
        contestPublic.roundLeaderboard(contestId, roundId),
        false,
      );
      setData(payload);
    } catch (e) {
      setData(null);
      if (e instanceof AppError && e.code === "RESULTS_NOT_AVAILABLE") {
        setNotAvailable(true);
        setError(null);
      } else {
        setError(e instanceof Error ? e.message : "Ошибка загрузки таблицы лидеров");
      }
    } finally {
      setLoading(false);
    }
  }, [contestId, roundId, enabled]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return { data, loading, error, notAvailable, refetch };
}
