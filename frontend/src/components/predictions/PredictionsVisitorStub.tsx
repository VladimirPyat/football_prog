interface PredictionsVisitorStubProps {
  /** Shown for logged-in participants — points to «Сделать прогноз». */
  showOwnPredictionHint?: boolean;
}

export function PredictionsVisitorStub({
  showOwnPredictionHint = false,
}: PredictionsVisitorStubProps) {
  return (
    <div
      className="bg-white border border-gray-200 rounded-lg p-8 text-center text-gray-600 space-y-2"
      data-testid="predictions-pre-deadline-stub"
    >
      <p>Будет доступно после дедлайна</p>
      {showOwnPredictionHint && (
        <p className="text-sm text-gray-500">
          Свой прогноз можно посмотреть и изменить в разделе «Сделать прогноз»
        </p>
      )}
    </div>
  );
}
