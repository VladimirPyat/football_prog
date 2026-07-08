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

export interface MatchPredictionOut {
  match_id: number;
  score1: number | null;
  score2: number | null;
}

export interface PredictionEntryOut {
  user_id: number;
  user_name: string | null;
  submitted: boolean;
  predictions: MatchPredictionOut[] | null;
}

export interface RoundPredictionsView {
  round_id: number;
  deadline_passed: boolean;
  matches: MatchOut[];
  entries: PredictionEntryOut[];
}

export interface PredictionBatchRequest {
  predictions: { match_id: number; score1: number; score2: number }[];
}

export interface PredictionBatchResponse {
  success: boolean;
  saved_count: number;
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

export interface MatchPointsOut {
  match_id: number;
  base_points: number | null;
}

export interface ScoreDetailOut {
  user_id: number;
  user_name: string;
  points_base: number;
  bonus1: number;
  bonus2: number;
  bonus3: number;
  total_without_bonus3: number;
  total_bonus_points?: number;
  total_with_bonus3: number;
  correct_outcomes: number;
  count_exact_high?: number;
  count_exact?: number;
  count_diff?: number;
  count_outcome?: number;
}

export interface LeaderboardEntryOut extends ScoreDetailOut {
  rank: number;
  predictions_count: number;
  exceptional_tiebreak_points: number;
  tiebreaker_status: string | null;
}

export interface LeaderboardOut {
  contest_id: number;
  round_id: number | null;
  round_number: number | null;
  bonuses_pending?: boolean;
  bonuses_pending_message?: string | null;
  leaderboard: LeaderboardEntryOut[];
}

export interface RoundResultRowOut {
  user_id: number;
  user_name: string;
  points: MatchPointsOut[];
  bonus1: number;
  bonus2: number;
  bonus3: number | null;
  total_without_bonus3: number;
  total: number;
  correct_outcomes: number;
}

export interface RoundResultsOut {
  round_id: number;
  matches: MatchOut[];
  results: RoundResultRowOut[];
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
