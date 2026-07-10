"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonVariant =
  | "primary"
  | "secondary"
  | "success"
  | "danger"
  | "dangerOutline"
  | "warning"
  | "indigo"
  | "ghostLink"
  | "link";
type ButtonSize = "sm" | "md";

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:
    "text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed",
  secondary: "border border-gray-300 text-gray-900 hover:bg-gray-50 disabled:opacity-50",
  success:
    "text-white bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed",
  danger:
    "text-white bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed",
  dangerOutline:
    "text-red-600 border border-red-300 bg-white hover:bg-red-50 disabled:opacity-50",
  warning:
    "text-white bg-amber-600 hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed",
  indigo:
    "text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed",
  ghostLink: "text-red-600 hover:underline bg-transparent border-0 shadow-none p-0",
  link: "text-blue-600 hover:underline bg-transparent border-0 shadow-none p-0",
};

const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: "px-3 py-1 text-sm",
  md: "px-4 py-2 text-sm font-medium",
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  fullWidth?: boolean;
  children: ReactNode;
}

export function Button({
  variant = "primary",
  size = "md",
  fullWidth = false,
  className = "",
  type = "button",
  children,
  ...rest
}: ButtonProps) {
  const isLink = variant === "ghostLink" || variant === "link";
  const radius = isLink ? "" : "rounded-lg shadow-sm";
  const sizeClass = isLink ? "text-sm" : SIZE_CLASSES[size];

  return (
    <button
      type={type}
      className={`${VARIANT_CLASSES[variant]} ${sizeClass} ${radius} ${
        fullWidth ? "w-full" : ""
      } ${className}`.trim()}
      {...rest}
    >
      {children}
    </button>
  );
}
