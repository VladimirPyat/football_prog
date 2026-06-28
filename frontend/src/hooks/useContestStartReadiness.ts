"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet } from "@/lib/api/client";
import { contestAdmin } from "@/lib/api/endpoints";
import {
  assessContestStartReadiness,
  type ContestStartReadiness,
} from "@/lib/admin/contestStartReadiness";
import type { ParticipantOut, TeamOut } from "@/types/api";

export function useContestStartReadiness(contestId: number, totalTeams: number) {
  const [teams, setTeams] = useState<TeamOut[]>([]);
  const [participants, setParticipants] = useState<ParticipantOut[]>([]);
  const [loading, setLoading] = useState(true);

  const refetch = useCallback(async (): Promise<ContestStartReadiness> => {
    setLoading(true);
    try {
      const [teamsData, participantsData] = await Promise.all([
        apiGet<TeamOut[]>(contestAdmin.teams.list(contestId)),
        apiGet<ParticipantOut[]>(contestAdmin.participants.list(contestId)),
      ]);
      setTeams(teamsData);
      setParticipants(participantsData);
      return assessContestStartReadiness({
        totalTeams,
        teamsCount: teamsData.length,
        participants: participantsData,
      });
    } finally {
      setLoading(false);
    }
  }, [contestId, totalTeams]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  useEffect(() => {
    const onChanged = () => void refetch();
    window.addEventListener("contest-setup-changed", onChanged);
    return () => window.removeEventListener("contest-setup-changed", onChanged);
  }, [refetch]);

  const readiness = useMemo(
    () =>
      assessContestStartReadiness({
        totalTeams,
        teamsCount: teams.length,
        participants,
      }),
    [totalTeams, teams.length, participants],
  );

  return {
    readiness,
    loading,
    refetch,
  };
}
