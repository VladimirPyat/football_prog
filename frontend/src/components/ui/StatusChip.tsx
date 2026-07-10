type StatusKind = "round" | "match" | "contest";

const ROUND_BADGE: Record<string, string> = {
  DRAFT: "bg-gray-100 text-gray-800",
  ACTIVE: "bg-green-100 text-green-800",
  CLOSED: "bg-orange-100 text-orange-800",
  CALCULATED: "bg-blue-100 text-blue-800",
  PUBLISHED: "bg-purple-100 text-purple-800",
};

const MATCH_BADGE: Record<string, string> = {
  SCHEDULED: "bg-gray-100 text-gray-800",
  POSTPONED: "bg-yellow-100 text-yellow-800",
  CANCELED: "bg-red-100 text-red-800",
  VOID: "bg-red-50 text-red-700 border border-red-300",
  FINISHED: "bg-green-100 text-green-800",
};

const CONTEST_BADGE: Record<string, string> = {
  DRAFT: "bg-gray-100 text-gray-600",
  RUNNING: "bg-green-100 text-green-800",
  PAUSED: "bg-orange-100 text-orange-800",
  FINISHED: "bg-gray-100 text-gray-600",
};

const BADGE_BASE = "inline-block text-xs font-semibold px-2 py-1 rounded";

function badgeClass(kind: StatusKind, status: string): string {
  const map =
    kind === "round" ? ROUND_BADGE : kind === "match" ? MATCH_BADGE : CONTEST_BADGE;
  return `${BADGE_BASE} ${map[status] ?? "bg-gray-100 text-gray-800"}`;
}

export interface StatusChipProps {
  kind: StatusKind;
  status: string;
  label: string;
  className?: string;
}

export function StatusChip({ kind, status, label, className = "" }: StatusChipProps) {
  return (
    <span className={`${badgeClass(kind, status)} ${className}`.trim()}>{label}</span>
  );
}
