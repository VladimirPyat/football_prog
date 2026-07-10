import type { UserRole } from "@/types/api";

export interface PredictionEntryLike {
  user_id: number;
  predictions: unknown[] | null;
}

export interface ViewerLike {
  id: number;
  role: UserRole;
}

export function shouldShowScore(
  entry: PredictionEntryLike,
  viewer: ViewerLike | null,
  deadlinePassed: boolean,
): boolean {
  if (deadlinePassed) return entry.predictions !== null;
  if (!viewer) return false;
  if (viewer.role === "SUPPORT") return entry.predictions !== null;
  if (entry.user_id === viewer.id) return entry.predictions !== null;
  return false;
}
