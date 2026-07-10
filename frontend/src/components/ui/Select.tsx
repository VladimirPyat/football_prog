import type { SelectHTMLAttributes } from "react";

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  labelClassName?: string;
}

export function Select({
  label,
  labelClassName = "text-sm text-gray-600 whitespace-nowrap",
  className = "",
  id,
  children,
  ...rest
}: SelectProps) {
  const select = (
    <select
      id={id}
      className={`border border-gray-300 rounded px-3 py-1.5 text-sm bg-white ${className}`.trim()}
      {...rest}
    >
      {children}
    </select>
  );

  if (!label) return select;

  return (
    <div className="flex items-center gap-2">
      <label htmlFor={id} className={labelClassName}>
        {label}
      </label>
      {select}
    </div>
  );
}
