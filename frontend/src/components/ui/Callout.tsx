import type { ReactNode } from "react";

type CalloutVariant = "info" | "warning" | "error" | "success";

const VARIANT_CLASSES: Record<CalloutVariant, string> = {
  info: "text-sm text-blue-700 bg-blue-50 border border-blue-200",
  warning: "text-sm text-amber-800 bg-amber-50 border border-amber-200",
  error: "text-sm text-red-600 bg-red-50 border border-red-200",
  success: "text-sm text-green-900 bg-green-50 border border-green-200",
};

export interface CalloutProps {
  variant?: CalloutVariant;
  children: ReactNode;
  className?: string;
}

export function Callout({ variant = "info", children, className = "" }: CalloutProps) {
  return (
    <p className={`rounded px-3 py-2 ${VARIANT_CLASSES[variant]} ${className}`.trim()}>
      {children}
    </p>
  );
}
