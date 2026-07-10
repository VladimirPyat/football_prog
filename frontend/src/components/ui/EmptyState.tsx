interface EmptyStateProps {
  message?: string;
  className?: string;
}

export function EmptyState({
  message = "Нет данных",
  className = "",
}: EmptyStateProps) {
  return (
    <p className={`text-gray-500 py-8 text-center ${className}`.trim()} role="status">
      {message}
    </p>
  );
}
