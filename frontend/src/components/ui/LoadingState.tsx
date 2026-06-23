interface LoadingStateProps {
  message?: string;
}

export function LoadingState({ message = "Загрузка…" }: LoadingStateProps) {
  return (
    <div className="flex items-center justify-center py-12 text-gray-500" role="status">
      <span>{message}</span>
    </div>
  );
}
