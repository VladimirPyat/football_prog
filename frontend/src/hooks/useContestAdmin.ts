"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiPatch } from "@/lib/api/client";
import { contests } from "@/lib/api/endpoints";
import { useContest } from "@/hooks/useContest";
import { resolveDefaultContestId } from "@/lib/contest/resolveDefaultContestId";
import type { ContestOut, ContestPatchRequest } from "@/types/api";

export function useContestAdmin() {
  const { contestId, contest, setContestId } = useContest();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const effectiveId = contestId ?? resolveDefaultContestId();

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await setContestId(effectiveId, true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  }, [effectiveId, setContestId]);

  useEffect(() => {
    if (contest && contest.id !== effectiveId) {
      void refetch();
    } else if (!contest) {
      void refetch();
    }
  }, [contest, effectiveId, refetch]);

  const patchContest = useCallback(
    async (body: ContestPatchRequest): Promise<ContestOut> => {
      const updated = await apiPatch<ContestOut>(contests.patch(effectiveId), body);
      await setContestId(effectiveId, true);
      return updated;
    },
    [effectiveId, setContestId],
  );

  const fetchContest = useCallback(async (): Promise<ContestOut> => {
    return apiGet<ContestOut>(contests.byId(effectiveId));
  }, [effectiveId]);

  const isStale = contest != null && contest.id !== effectiveId;

  return {
    contestId: effectiveId,
    contest,
    loading: loading || isStale,
    error,
    refetch,
    patchContest,
    fetchContest,
  };
}
