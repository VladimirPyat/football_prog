"use client";

import { useCallback, useState } from "react";
import { AppError, apiPost } from "@/lib/api/client";
import { contestAdmin } from "@/lib/api/endpoints";
import { ERROR_CODES } from "@/lib/api/errors";
import { useToast } from "@/hooks/useToast";
import type { PredictionBatchRequest, PredictionBatchResponse } from "@/types/api";

export function usePredictionSubmit(contestId: number, roundId: number) {
  const { showToast } = useToast();
  const [submitting, setSubmitting] = useState(false);

  const submit = useCallback(
    async (body: PredictionBatchRequest): Promise<boolean> => {
      setSubmitting(true);
      try {
        await apiPost<PredictionBatchResponse>(
          contestAdmin.rounds.predictions(contestId, roundId),
          body,
        );
        showToast("success", "Прогноз сохранён");
        return true;
      } catch (e) {
        if (e instanceof AppError) {
          if (e.code === ERROR_CODES.DEADLINE_PASSED) {
            showToast("error", "Дедлайн прошёл — изменения невозможны");
          } else {
            showToast("error", e.detail);
          }
        } else {
          showToast("error", "Не удалось сохранить прогноз");
        }
        return false;
      } finally {
        setSubmitting(false);
      }
    },
    [contestId, roundId, showToast],
  );

  return { submit, submitting };
}
