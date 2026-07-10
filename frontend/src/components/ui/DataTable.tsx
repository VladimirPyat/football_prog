import type { ReactNode } from "react";

export interface DataTableProps {
  children: ReactNode;
  variant?: "contest" | "admin";
  testId?: string;
  className?: string;
}

export function DataTable({
  children,
  variant = "contest",
  testId,
  className = "",
}: DataTableProps) {
  if (variant === "contest") {
    return (
      <div
        className={`bg-white border border-gray-200 rounded-lg overflow-x-auto ${className}`.trim()}
        data-testid={testId}
      >
        <table className="border-collapse text-sm w-max max-w-full">{children}</table>
      </div>
    );
  }

  return (
    <div
      className={`overflow-x-auto border border-gray-200 rounded-lg ${className}`.trim()}
      data-testid={testId}
    >
      <table className="min-w-full text-sm">{children}</table>
    </div>
  );
}
