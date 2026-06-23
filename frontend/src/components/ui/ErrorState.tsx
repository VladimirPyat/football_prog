interface ErrorStateProps {
  message?: string;
}

export function ErrorState({ message = "Произошла ошибка" }: ErrorStateProps) {
  return (
    <div className="flex items-center justify-center py-12 text-red-600" role="alert">
      <span>{message}</span>
    </div>
  );
}
