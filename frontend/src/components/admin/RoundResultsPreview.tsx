"use client";

import { ResultsMatrix } from "@/components/contest/ResultsMatrix";
import { LoadingState } from "@/components/ui/LoadingState";
import { useRoundResults } from "@/hooks/useRoundResults";

interface RoundResultsPreviewProps {
  contestId: number;
  roundId: number;
  roundNumber: number;
  preview?: boolean;
}

export function RoundResultsPreview({
  contestId,
  roundId,
  roundNumber,
  preview = false,
}: RoundResultsPreviewProps) {
  const { data, loading, error, pointsMissing } = useRoundResults(contestId, roundId, true);

  if (loading) {
    return <LoadingState message="Загрузка результатов тура…" />;
  }
  if (error) {
    return <p className="text-sm text-red-600">{error}</p>;
  }
  if (!data?.rows.length) {
    return <p className="text-sm text-gray-500">Очки не рассчитаны или участники отсутствуют.</p>;
  }
  if (pointsMissing) {
    return (
      <p className="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded px-3 py-2">
        Очки по матчам ещё не рассчитаны.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {preview && (
        <span className="inline-block text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
          Предпросмотр — тур ещё не опубликован
        </span>
      )}
      <ResultsMatrix
        matches={data.matches}
        rows={data.rows}
        roundLabel={`Тур ${roundNumber}`}
      />
    </div>
  );
}
