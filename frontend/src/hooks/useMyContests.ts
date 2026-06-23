"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "@/lib/api/client";
import { me } from "@/lib/api/endpoints";
import { resolveDefaultContestId } from "@/lib/contest/resolveDefaultContestId";
import type { AppError } from "@/lib/api/client";
import type { ContestListItem, UserContestOut } from "@/types/api";

interface UseMyContestsResult {
  contests: ContestListItem[];
  loading: boolean;
  error: AppError | null;
  refetch: () => Promise<void>;
  isFallback: boolean;
}

function toListItem(c: UserContestOut): ContestListItem {
  return { id: c.id, name: c.name, status: c.status };
}

function fallbackContest(): ContestListItem {
  return {
    id: resolveDefaultContestId(),
    name: "Конкурс по умолчанию",
    status: "RUNNING",
  };
}

export function useMyContests(enabled = true): UseMyContestsResult {
  const [contests, setContests] = useState<ContestListItem[]>([]);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState<AppError | null>(null);
  const [isFallback, setIsFallback] = useState(false);

  const refetch = useCallback(async () => {
    if (!enabled) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet<UserContestOut[]>(me.contests());
      if (!data.length) {
        setContests([fallbackContest()]);
        setIsFallback(true);
      } else {
        setContests(data.map(toListItem));
        setIsFallback(false);
      }
    } catch (err) {
      setError(err as AppError);
      setContests([fallbackContest()]);
      setIsFallback(true);
    } finally {
      setLoading(false);
    }
  }, [enabled]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return { contests, loading, error, refetch, isFallback };
}
