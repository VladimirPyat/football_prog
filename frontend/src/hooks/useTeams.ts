"use client";

import { useCallback, useEffect, useState } from "react";
import { apiDelete, apiGet, apiPatch, apiPost, apiUpload } from "@/lib/api/client";
import { contestAdmin } from "@/lib/api/endpoints";
import type { TeamOut } from "@/types/api";

export function useTeams(contestId: number) {
  const [teams, setTeams] = useState<TeamOut[]>([]);
  const [loading, setLoading] = useState(true);

  const refetch = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiGet<TeamOut[]>(contestAdmin.teams.list(contestId));
      setTeams(data);
    } finally {
      setLoading(false);
    }
  }, [contestId]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  const createTeam = useCallback(
    async (body: { name: string; short_name: string }) => {
      await apiPost<TeamOut>(contestAdmin.teams.create(contestId), body);
      await refetch();
      window.dispatchEvent(new Event("contest-setup-changed"));
    },
    [contestId, refetch],
  );

  const patchTeam = useCallback(
    async (teamId: number, body: { name?: string; short_name?: string }) => {
      await apiPatch<TeamOut>(contestAdmin.teams.patch(contestId, teamId), body);
      await refetch();
    },
    [contestId, refetch],
  );

  const deleteTeam = useCallback(
    async (teamId: number) => {
      await apiDelete(contestAdmin.teams.delete(contestId, teamId));
      await refetch();
      window.dispatchEvent(new Event("contest-setup-changed"));
    },
    [contestId, refetch],
  );

  const uploadLogo = useCallback(
    async (teamId: number, file: File) => {
      const res = await apiUpload<{ logo_url: string }>(
        contestAdmin.teams.logo(contestId, teamId),
        file,
      );
      await refetch();
      return res.logo_url;
    },
    [contestId, refetch],
  );

  return { teams, loading, refetch, createTeam, patchTeam, deleteTeam, uploadLogo };
}
