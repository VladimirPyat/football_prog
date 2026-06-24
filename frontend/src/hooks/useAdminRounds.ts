"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiPatch, apiPost } from "@/lib/api/client";
import { contestAdmin } from "@/lib/api/endpoints";
import type { CreateRoundResponse, RoundOut } from "@/types/api";

export function useAdminRounds(contestId: number) {
  const [rounds, setRounds] = useState<RoundOut[]>([]);
  const [loading, setLoading] = useState(true);

  const refetch = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiGet<RoundOut[]>(contestAdmin.rounds.list(contestId));
      setRounds(data.sort((a, b) => a.number - b.number));
    } finally {
      setLoading(false);
    }
  }, [contestId]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  const createRound = useCallback(
    async (body: {
      number: number;
      deadline: string;
      matches: { team1_id: number; team2_id: number; date_time: string }[];
    }): Promise<CreateRoundResponse> => {
      const res = await apiPost<CreateRoundResponse>(contestAdmin.rounds.create(contestId), body);
      await refetch();
      return res;
    },
    [contestId, refetch],
  );

  const activateRound = useCallback(
    async (roundId: number) => {
      await apiPost(contestAdmin.rounds.activate(contestId, roundId), {});
      await refetch();
    },
    [contestId, refetch],
  );

  const updateRound = useCallback(
    async (
      roundId: number,
      body: {
        deadline?: string;
        matches?: { match_id: number; date_time?: string; status?: string }[];
      },
    ) => {
      await apiPatch(contestAdmin.rounds.patch(contestId, roundId), body);
      await refetch();
    },
    [contestId, refetch],
  );

  const closeRound = useCallback(
    async (roundId: number) => {
      await apiPost(contestAdmin.rounds.close(contestId, roundId), {});
      await refetch();
    },
    [contestId, refetch],
  );

  const calculateRound = useCallback(
    async (roundId: number) => {
      await apiPost(contestAdmin.rounds.calculate(contestId, roundId), {});
      await refetch();
    },
    [contestId, refetch],
  );

  const publishRound = useCallback(
    async (roundId: number) => {
      await apiPost(contestAdmin.rounds.publish(contestId, roundId), {});
      await refetch();
    },
    [contestId, refetch],
  );

  const createFreeTour = useCallback(
    async (body: { deadline: string; matches: { match_id: number; new_date_time: string }[] }) => {
      await apiPost(contestAdmin.rounds.freeTour(contestId), body);
      await refetch();
    },
    [contestId, refetch],
  );

  return {
    rounds,
    loading,
    refetch,
    createRound,
    activateRound,
    updateRound,
    closeRound,
    calculateRound,
    publishRound,
    createFreeTour,
  };
}
