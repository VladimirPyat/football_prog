export function DeadlineCountdown({ label }: { label: string }) {
  return (
    <p className="text-sm text-gray-700" data-testid="deadline-countdown">
      До дедлайна: <span className="font-medium">{label}</span>
    </p>
  );
}
