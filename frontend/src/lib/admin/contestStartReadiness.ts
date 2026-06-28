import type { ParticipantStatus } from "@/types/api";

export const MIN_ACCEPTED_PARTICIPANTS_FOR_START = 2;

export interface ContestStartReadinessInput {
  totalTeams: number;
  teamsCount: number;
  participants: { status: ParticipantStatus }[];
}

export interface ContestStartReadiness {
  teamsOk: boolean;
  participantsOk: boolean;
  ready: boolean;
  acceptedCount: number;
  teamsCount: number;
  totalTeams: number;
  issues: string[];
}

export function assessContestStartReadiness(
  input: ContestStartReadinessInput,
): ContestStartReadiness {
  const acceptedCount = input.participants.filter((p) => p.status === "ACCEPTED").length;
  const teamsOk = input.teamsCount === input.totalTeams;
  const participantsOk = acceptedCount >= MIN_ACCEPTED_PARTICIPANTS_FOR_START;
  const issues: string[] = [];

  if (!teamsOk) {
    issues.push(`Добавьте все команды: ${input.teamsCount} из ${input.totalTeams}`);
  }
  if (!participantsOk) {
    issues.push(
      `Нужно минимум ${MIN_ACCEPTED_PARTICIPANTS_FOR_START} участника со статусом «Принято» (сейчас: ${acceptedCount})`,
    );
  }

  return {
    teamsOk,
    participantsOk,
    ready: teamsOk && participantsOk,
    acceptedCount,
    teamsCount: input.teamsCount,
    totalTeams: input.totalTeams,
    issues,
  };
}
