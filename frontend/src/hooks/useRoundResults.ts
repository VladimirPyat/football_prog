"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AppError, apiGet } from "@/lib/api/client";
import { contestPublic } from "@/lib/api/endpoints";
import {
  mapResultsMatrixMatch,
  mapRoundResultsRows,
  roundResultsPointsMissing,
  type ResultsMatrixMatch,
  type ResultsMatrixRow,
} from "@/lib/results/mapRoundResultsRow";
import type { RoundResultsOut } from "@/types/api";

export interface RoundResultsView {
  matches: ResultsMatrixMatch[];
  rows: ResultsMatrixRow[];
}

export function useRoundResults(contestId: number, roundId: number | null, enabled = true) {
  const [raw, setRaw] = useState<RoundResultsOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notAvailable, setNotAvailable] = useState(false);
  const [pointsMissing, setPointsMissing] = useState(false);

  const refetch = useCallback(async () => {
    if (!roundId || !enabled) {
      setRaw(null);
      setError(null);
      setNotAvailable(false);
      setPointsMissing(false);
      return;
    }
    setLoading(true);
    setError(null);
    setNotAvailable(false);
    setPointsMissing(false);
    try {
      const payload = await apiGet<RoundResultsOut>(
        contestPublic.roundResults(contestId, roundId),
        false,
      );
      setRaw(payload);
      if (roundResultsPointsMissing(payload.matches, payload.results)) {
        setPointsMissing(true);
      }
    } catch (e) {
      setRaw(null);
      if (e instanceof AppError && e.code === "RESULTS_NOT_AVAILABLE") {
        setNotAvailable(true);
        setError(null);
      } else {
        setError(e instanceof Error ? e.message : "Ошибка загрузки результатов");
      }
    } finally {
      setLoading(false);
    }
  }, [contestId, roundId, enabled]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  const data = useMemo<RoundResultsView | null>(() => {
    if (!raw) return null;
    const matchIds = raw.matches.map((match) => match.id);
    return {
      matches: raw.matches.map(mapResultsMatrixMatch),
      rows: mapRoundResultsRows(raw.results, matchIds),
    };
  }, [raw]);

  return { data, loading, error, notAvailable, pointsMissing, refetch };
}
