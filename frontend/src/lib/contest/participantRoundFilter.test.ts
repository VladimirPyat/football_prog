import { describe, expect, it } from "vitest";
import type { RoundOut } from "@/types/api";
import { filterParticipantVisibleRounds } from "./participantRoundFilter";

const rounds: RoundOut[] = [
  {
    id: 1,
    contest_id: 1,
    number: 1,
    status: "CLOSED",
    kind: "REGULAR",
    deadline: "2026-01-01T12:00:00Z",
    matches_count: 2,
    supplementary_index: null,
    source_round_numbers: [],
  },
  {
    id: 2,
    contest_id: 1,
    number: 2,
    status: "ACTIVE",
    kind: "REGULAR",
    deadline: "2026-06-01T12:00:00Z",
    matches_count: 2,
    supplementary_index: null,
    source_round_numbers: [],
  },
  {
    id: 3,
    contest_id: 1,
    number: 3,
    status: "DRAFT",
    kind: "REGULAR",
    deadline: "2026-07-01T12:00:00Z",
    matches_count: 2,
    supplementary_index: null,
    source_round_numbers: [],
  },
];

describe("filterParticipantVisibleRounds", () => {
  it("hides DRAFT rounds for participants and visitors", () => {
    expect(filterParticipantVisibleRounds(rounds)).toHaveLength(2);
    expect(filterParticipantVisibleRounds(rounds, "USER")).toHaveLength(2);
    expect(filterParticipantVisibleRounds(rounds, null)).toHaveLength(2);
  });

  it("keeps DRAFT rounds for staff", () => {
    expect(filterParticipantVisibleRounds(rounds, "SUPERVISOR")).toHaveLength(3);
    expect(filterParticipantVisibleRounds(rounds, "ADMIN")).toHaveLength(3);
  });
});
