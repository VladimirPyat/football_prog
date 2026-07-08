import { ROUND_NOT_PUBLISHED_COPY } from "@/lib/contest/roundPublicVisibility";

interface ResultsUnavailableMessageProps {
  message?: string;
}

export function ResultsUnavailableMessage({
  message = ROUND_NOT_PUBLISHED_COPY,
}: ResultsUnavailableMessageProps) {
  return (
    <div
      className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-8 text-center text-gray-600"
      data-testid="results-unavailable"
    >
      {message}
    </div>
  );
}
