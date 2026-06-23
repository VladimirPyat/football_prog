export type UserRole = "USER" | "SUPERVISOR" | "ADMIN";

export type ContestStatus = "DRAFT" | "RUNNING" | "PAUSED" | "FINISHED";

export type ParticipantStatus = "PENDING" | "ACCEPTED";

export interface UserOut {
  id: number;
  login: string;
  role: UserRole;
  first_name: string;
  last_name: string;
  is_temp_password: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  is_temp_password: boolean;
}

export interface ContactOut {
  email: string | null;
  vk_id: string | null;
  tg_id: string | null;
  notify_enabled: boolean;
}

export interface ContactPatchRequest {
  email?: string | null;
  vk_id?: string | null;
  tg_id?: string | null;
  notify_enabled?: boolean | null;
}

export interface UserContestOut {
  id: number;
  name: string;
  status: ContestStatus;
  participant_status: ParticipantStatus;
  role?: UserRole;
  slug: string | null;
}

export interface PublicContestOut {
  id: number;
  name: string;
  status: ContestStatus;
  slug: string | null;
}

export interface ContestOut {
  id: number;
  name: string;
  slug: string | null;
  is_locked: boolean;
  status: ContestStatus;
  paused_at: string | null;
  finished_at: string | null;
  total_teams: number;
  matches_per_round: number;
  total_rounds: number;
  is_round_robin: boolean;
  rules_json: Record<string, unknown>;
}

export interface ChangePasswordRequest {
  old_password: string;
  new_password: string;
}

/** Minimal contest item for lists and picker */
export interface ContestListItem {
  id: number;
  name: string;
  status: ContestStatus;
}
