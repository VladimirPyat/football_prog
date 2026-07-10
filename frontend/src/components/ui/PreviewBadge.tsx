const DEFAULT_LABEL = "Предпросмотр — тур ещё не опубликован";

export function PreviewBadge({ label = DEFAULT_LABEL }: { label?: string }) {
  return (
    <span className="inline-block text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
      {label}
    </span>
  );
}
