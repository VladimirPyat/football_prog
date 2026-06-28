"use client";

import { useCallback, useEffect, useState } from "react";
import { apiDelete, apiGet, apiPost, apiPut } from "@/lib/api/client";
import { contestAdmin } from "@/lib/api/endpoints";
import type { ParticipantInviteOut, ParticipantOut } from "@/types/api";

export function useParticipants(contestId: number) {
  const [participants, setParticipants] = useState<ParticipantOut[]>([]);
  const [loading, setLoading] = useState(true);

  const refetch = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiGet<ParticipantOut[]>(contestAdmin.participants.list(contestId));
      setParticipants(data);
    } finally {
      setLoading(false);
    }
  }, [contestId]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  const invite = useCallback(
    async (body: {
      email: string;
      first_name: string;
      last_name: string;
      login?: string;
    }): Promise<ParticipantInviteOut> => {
      const res = await apiPost<ParticipantInviteOut>(
        contestAdmin.participants.create(contestId),
        body,
      );
      await refetch();
      window.dispatchEvent(new Event("contest-setup-changed"));
      return res;
    },
    [contestId, refetch],
  );

  const remove = useCallback(
    async (userId: number) => {
      await apiDelete(contestAdmin.participants.delete(contestId, userId));
      await refetch();
      window.dispatchEvent(new Event("contest-setup-changed"));
    },
    [contestId, refetch],
  );

  const setTiebreak = useCallback(
    async (userId: number, points: number) => {
      await apiPut(contestAdmin.participants.tiebreak(contestId, userId), { points });
      await refetch();
    },
    [contestId, refetch],
  );

  return { participants, loading, refetch, invite, remove, setTiebreak };
}
