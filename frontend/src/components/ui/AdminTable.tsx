import type { ReactNode } from "react";
import { DataTable } from "@/components/ui/DataTable";
import { TH_ADMIN } from "@/lib/table/tableHeaderStyles";

export interface AdminTableProps {
  headers: ReactNode;
  children: ReactNode;
  testId?: string;
  className?: string;
}

export function AdminTh({
  children,
  className = "",
  align = "left",
}: {
  children: ReactNode;
  className?: string;
  align?: "left" | "right" | "center";
}) {
  const alignClass =
    align === "right" ? "text-right" : align === "center" ? "text-center" : "text-left";
  return <th className={`${TH_ADMIN} ${alignClass} ${className}`.trim()}>{children}</th>;
}

export function AdminTable({ headers, children, testId, className }: AdminTableProps) {
  return (
    <DataTable variant="admin" testId={testId} className={className}>
      <thead className="bg-gray-50">
        <tr>{headers}</tr>
      </thead>
      <tbody>{children}</tbody>
    </DataTable>
  );
}
