"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { getActiveContestId, setActiveContestId } from "@/lib/auth/token";
import { fetchContestDetails } from "@/lib/contest/fetchContestDetails";
import { resolveDefaultContestId } from "@/lib/contest/resolveDefaultContestId";
import type { ContestOut } from "@/types/api";

interface ContestContextValue {
  contestId: number | null;
  contest: ContestOut | null;
  isLocked: boolean;
  status: ContestOut["status"] | null;
  maxScore: number;
  rules: Record<string, unknown>;
  setContestId: (id: number, fetchDetails?: boolean) => Promise<void>;
}

const ContestContext = createContext<ContestContextValue | null>(null);

function extractMaxScore(rules: Record<string, unknown>): number {
  const constraints = rules.constraints as Record<string, unknown> | undefined;
  const range = constraints?.score_validation_range as number[] | undefined;
  if (Array.isArray(range) && range.length >= 2) return range[1];
  return 20;
}

export function ContestProvider({ children }: { children: ReactNode }) {
  const [contestId, setContestIdState] = useState<number | null>(null);
  const [contest, setContest] = useState<ContestOut | null>(null);

  useEffect(() => {
    const stored = getActiveContestId();
    setContestIdState(stored ?? resolveDefaultContestId());
  }, []);

  const setContestId = useCallback(async (id: number, fetchDetails = false) => {
    setContestIdState(id);
    setActiveContestId(id);
    if (fetchDetails) {
      try {
        const details = await fetchContestDetails(id);
        setContest(details);
      } catch {
        setContest(null);
      }
    }
  }, []);

  useEffect(() => {
    if (contestId == null) return;
    if (contest == null || contest.id !== contestId) {
      void setContestId(contestId, true);
    }
  }, [contestId, contest, setContestId]);

  const value = useMemo<ContestContextValue>(() => {
    const rules = (contest?.rules_json ?? {}) as Record<string, unknown>;
    return {
      contestId: contestId ?? resolveDefaultContestId(),
      contest,
      isLocked: contest?.is_locked ?? false,
      status: contest?.status ?? null,
      maxScore: extractMaxScore(rules),
      rules,
      setContestId,
    };
  }, [contestId, contest, setContestId]);

  return <ContestContext.Provider value={value}>{children}</ContestContext.Provider>;
}

export function useContestContext(): ContestContextValue {
  const ctx = useContext(ContestContext);
  if (!ctx) throw new Error("useContestContext must be used within ContestProvider");
  return ctx;
}
