"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "@/lib/api/client";
import { contestAdmin } from "@/lib/api/endpoints";
import type { RoundPredictionsView } from "@/types/api";

export function usePredictionsView(contestId: number, roundId: number | null, enabled = true) {
  const [data, setData] = useState<RoundPredictionsView | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    if (!roundId || !enabled) return;
    setLoading(true);
    setError(null);
    try {
      const view = await apiGet<RoundPredictionsView>(
        contestAdmin.rounds.predictions(contestId, roundId),
      );
      setData(view);
    } catch (e) {
      setData(null);
      setError(e instanceof Error ? e.message : "Ошибка загрузки прогнозов");
    } finally {
      setLoading(false);
    }
  }, [contestId, roundId, enabled]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  useEffect(() => {
    if (!enabled || !roundId) return;
    const onFocus = () => void refetch();
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [refetch, enabled, roundId]);

  useEffect(() => {
    if (!enabled || !roundId || data?.deadline_passed) return;
    const id = setInterval(() => void refetch(), 60_000);
    return () => clearInterval(id);
  }, [refetch, enabled, roundId, data?.deadline_passed]);

  return { data, loading, error, refetch };
}
