"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "@/lib/api/client";
import { contests } from "@/lib/api/endpoints";
import type { AppError } from "@/lib/api/client";
import type { ContestListItem, PublicContestOut } from "@/types/api";

interface UsePublicContestsResult {
  contests: ContestListItem[];
  loading: boolean;
  error: AppError | null;
  refetch: () => Promise<void>;
}

function toListItem(c: PublicContestOut): ContestListItem {
  return { id: c.id, name: c.name, status: c.status };
}

export function usePublicContests(): UsePublicContestsResult {
  const [contestList, setContestList] = useState<ContestListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<AppError | null>(null);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet<PublicContestOut[]>(contests.public(), false);
      setContestList(data.map(toListItem));
    } catch (err) {
      setError(err as AppError);
      setContestList([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return { contests: contestList, loading, error, refetch };
}
