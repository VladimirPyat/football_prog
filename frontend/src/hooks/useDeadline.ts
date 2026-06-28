"use client";

import { useCallback, useEffect, useState } from "react";
import { parseApiUtc } from "@/lib/datetime/parseApiUtc";
import type { RoundOut } from "@/types/api";

export interface DeadlineState {
  deadlinePassed: boolean;
  secondsLeft: number;
  label: string;
}

function computeDeadlineState(deadlineIso: string, apiDeadlinePassed?: boolean): DeadlineState {
  const deadlineMs = parseApiUtc(deadlineIso);
  const now = Date.now();
  const secondsLeft = Math.max(0, Math.floor((deadlineMs - now) / 1000));
  const deadlinePassed = apiDeadlinePassed === true || now >= deadlineMs;

  if (deadlinePassed) {
    return { deadlinePassed: true, secondsLeft: 0, label: "Дедлайн прошёл" };
  }

  const days = Math.floor(secondsLeft / 86400);
  const hours = Math.floor((secondsLeft % 86400) / 3600);
  const minutes = Math.floor((secondsLeft % 3600) / 60);
  const secs = secondsLeft % 60;

  let label: string;
  if (days > 0) {
    label = `${days} д ${hours} ч ${minutes} мин`;
  } else if (hours > 0) {
    label = `${hours} ч ${minutes} мин ${secs} с`;
  } else {
    label = `${minutes} мин ${secs} с`;
  }

  return { deadlinePassed: false, secondsLeft, label };
}

export function useDeadline(round: RoundOut | null, apiDeadlinePassed?: boolean) {
  const [state, setState] = useState<DeadlineState>(() =>
    round
      ? computeDeadlineState(round.deadline, apiDeadlinePassed)
      : { deadlinePassed: false, secondsLeft: 0, label: "" },
  );

  const tick = useCallback(() => {
    if (!round) return;
    setState(computeDeadlineState(round.deadline, apiDeadlinePassed));
  }, [round, apiDeadlinePassed]);

  useEffect(() => {
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [tick]);

  return state;
}
