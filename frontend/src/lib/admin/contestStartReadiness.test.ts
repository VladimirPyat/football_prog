import { describe, expect, it } from "vitest";
import { assessContestStartReadiness } from "@/lib/admin/contestStartReadiness";

describe("assessContestStartReadiness", () => {
  it("ready when teams match and at least two accepted participants", () => {
    const result = assessContestStartReadiness({
      totalTeams: 8,
      teamsCount: 8,
      participants: [{ status: "ACCEPTED" }, { status: "ACCEPTED" }, { status: "PENDING" }],
    });
    expect(result.ready).toBe(true);
    expect(result.issues).toHaveLength(0);
  });

  it("not ready when teams are incomplete", () => {
    const result = assessContestStartReadiness({
      totalTeams: 8,
      teamsCount: 1,
      participants: [{ status: "ACCEPTED" }, { status: "ACCEPTED" }],
    });
    expect(result.ready).toBe(false);
    expect(result.teamsOk).toBe(false);
    expect(result.issues[0]).toContain("1 из 8");
  });

  it("not ready when accepted participants are below minimum", () => {
    const result = assessContestStartReadiness({
      totalTeams: 4,
      teamsCount: 4,
      participants: [{ status: "PENDING" }, { status: "ACCEPTED" }],
    });
    expect(result.ready).toBe(false);
    expect(result.participantsOk).toBe(false);
    expect(result.issues.some((issue) => issue.includes("Принято"))).toBe(true);
  });
});
