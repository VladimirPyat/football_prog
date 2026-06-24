"use client";

import { useCallback } from "react";
import { apiPatch, apiPut } from "@/lib/api/client";
import { contestAdmin } from "@/lib/api/endpoints";
import type { MatchStatus, MatchStatusPatchResponse } from "@/types/api";

export function useAdminResults(contestId: number) {
  const putResult = useCallback(
    async (matchId: number, score1: number, score2: number) => {
      await apiPut(contestAdmin.matches.result(contestId, matchId), {
        score1,
        score2,
        status: "FINISHED",
      });
    },
    [contestId],
  );

  const patchStatus = useCallback(
    async (matchId: number, status: MatchStatus): Promise<MatchStatusPatchResponse> => {
      return apiPatch<MatchStatusPatchResponse>(contestAdmin.matches.status(contestId, matchId), {
        status,
      });
    },
    [contestId],
  );

  return { putResult, patchStatus };
}
