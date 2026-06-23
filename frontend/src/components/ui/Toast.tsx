interface ToastProps {
  type: "success" | "error";
  message: string;
}

export function Toast({ type, message }: ToastProps) {
  const bg = type === "success" ? "bg-green-600" : "bg-red-600";
  return (
    <div className={`${bg} text-white px-4 py-3 rounded shadow-lg text-sm max-w-sm`} role="alert">
      {message}
    </div>
  );
}
