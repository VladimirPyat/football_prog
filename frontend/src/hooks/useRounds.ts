"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "@/lib/api/client";
import { contestAdmin } from "@/lib/api/endpoints";
import type { RoundOut } from "@/types/api";

export function useRounds(contestId: number) {
  const [rounds, setRounds] = useState<RoundOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet<RoundOut[]>(contestAdmin.rounds.list(contestId), false);
      setRounds(data.sort((a, b) => a.number - b.number));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки туров");
      setRounds([]);
    } finally {
      setLoading(false);
    }
  }, [contestId]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  const activeRound = rounds.find((r) => r.status === "ACTIVE") ?? null;

  return { rounds, activeRound, loading, error, refetch };
}
