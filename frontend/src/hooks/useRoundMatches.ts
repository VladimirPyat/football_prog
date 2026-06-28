"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiGet } from "@/lib/api/client";
import { contestAdmin } from "@/lib/api/endpoints";
import type { RoundPredictionsView } from "@/types/api";

export function useRoundMatches(
  contestId: number,
  roundId: number | null,
  options?: { onDeadlinePassed?: () => void },
) {
  const [view, setView] = useState<RoundPredictionsView | null>(null);
  const [loading, setLoading] = useState(false);
  const prevDeadlinePassedRef = useRef<boolean | null>(null);
  const onDeadlinePassedRef = useRef(options?.onDeadlinePassed);
  onDeadlinePassedRef.current = options?.onDeadlinePassed;

  const refetch = useCallback(async () => {
    if (!roundId) {
      setView(null);
      prevDeadlinePassedRef.current = null;
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

  useEffect(() => {
    prevDeadlinePassedRef.current = null;
  }, [roundId]);

  useEffect(() => {
    const passed = view?.deadline_passed ?? false;
    const prev = prevDeadlinePassedRef.current;
    if (passed && prev !== true) {
      onDeadlinePassedRef.current?.();
    }
    prevDeadlinePassedRef.current = passed;
  }, [view?.deadline_passed]);

  return {
    view,
    matches: view?.matches ?? [],
    deadlinePassed: view?.deadline_passed ?? false,
    loading,
    refetch,
  };
}
