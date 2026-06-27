export function LockBanner() {
  return (
    <div
      className="mb-4 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900"
      role="status"
    >
      Редактирование параметров недоступно — конкурс уже запущен. Изменение правил scoring или
      состава команд невозможно.
    </div>
  );
}
