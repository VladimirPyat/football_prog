export function DeadlineWarningBanner() {
  return (
    <div
      className="bg-amber-50 border border-amber-200 text-amber-900 rounded-lg px-4 py-3 text-sm"
      role="alert"
      data-testid="deadline-warning-banner"
    >
      До дедлайна осталось менее 24 часов. Успейте сохранить прогноз.
    </div>
  );
}
