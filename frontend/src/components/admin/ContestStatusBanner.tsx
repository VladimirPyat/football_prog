interface ContestStatusBannerProps {
  status: "PAUSED" | "FINISHED";
}

export function ContestStatusBanner({ status }: ContestStatusBannerProps) {
  const text =
    status === "PAUSED"
      ? "Конкурс на паузе. Все операции изменения данных временно недоступны."
      : "Конкурс завершён. Редактирование ограничено.";

  return (
    <div
      className="mb-4 rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-900"
      role="status"
    >
      {text}
    </div>
  );
}
