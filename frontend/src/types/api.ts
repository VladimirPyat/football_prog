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

export interface DeletedContestOut {
  id: number;
  name: string;
  deleted_at: string;
  restore_available: boolean;
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

export type RoundStatus = "DRAFT" | "ACTIVE" | "CLOSED" | "CALCULATED" | "PUBLISHED";

export type MatchStatus = "SCHEDULED" | "POSTPONED" | "CANCELED" | "VOID" | "FINISHED";

export interface TeamOut {
  id: number;
  contest_id: number;
  name: string;
  short_name: string;
  logo_url: string;
}

export interface ParticipantOut {
  user_id: number;
  login: string;
  first_name: string;
  last_name: string;
  email: string | null;
  status: ParticipantStatus;
  exceptional_tiebreak_points: number;
}

export interface ParticipantInviteOut {
  user_id: number;
  login: string;
  temp_password: string;
  status: ParticipantStatus;
  setup_url: string;
}

export interface PasswordResetResponse {
  message: string;
}

export interface RoundOut {
  id: number;
  contest_id: number;
  number: number;
  deadline: string;
  status: RoundStatus;
  matches_count: number;
  kind: "REGULAR" | "SUPPLEMENTARY";
  supplementary_index: number | null;
  source_round_numbers: number[];
}

export interface MatchOut {
  id: number;
  team1_id?: number;
  team2_id?: number;
  team1: string;
  team2: string;
  date_time: string;
  score1: number | null;
  score2: number | null;
  status: MatchStatus;
}

export interface RoundPredictionsView {
  round_id: number;
  deadline_passed: boolean;
  matches: MatchOut[];
  entries: unknown[];
}

export interface CreateRoundResponse {
  round_id: number;
  status: RoundStatus;
}

export interface MatchStatusPatchResponse {
  recalculation_triggered?: boolean;
}

export interface CreateSupervisorResponse {
  user: UserOut;
}

export interface ContestPatchRequest {
  name?: string;
  slug?: string | null;
  total_teams?: number;
  matches_per_round?: number;
  total_rounds?: number;
  is_round_robin?: boolean;
  rules_json?: Record<string, unknown>;
}

export interface CreateContestRequest {
  name: string;
  slug?: string | null;
  total_teams?: number;
  matches_per_round?: number;
  total_rounds?: number;
  is_round_robin?: boolean;
}
