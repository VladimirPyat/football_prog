import { describe, it, expect } from "vitest";
import { isRoundPubliclyVisible } from "@/lib/contest/roundPublicVisibility";
import type { RoundStatus } from "@/types/api";

describe("roundPublicVisibility", () => {
  it("[UI-PUBLIC-LB-GATE] returns true only for PUBLISHED", () => {
    const statuses: RoundStatus[] = ["DRAFT", "ACTIVE", "CLOSED", "CALCULATED", "PUBLISHED"];
    for (const status of statuses) {
      if (status === "PUBLISHED") {
        expect(isRoundPubliclyVisible(status)).toBe(true);
      } else {
        expect(isRoundPubliclyVisible(status)).toBe(false);
      }
    }
  });

  it("DRAFT round is not publicly visible", () => {
    expect(isRoundPubliclyVisible("DRAFT")).toBe(false);
  });

  it("ACTIVE round is not publicly visible", () => {
    expect(isRoundPubliclyVisible("ACTIVE")).toBe(false);
  });

  it("CLOSED round is not publicly visible", () => {
    expect(isRoundPubliclyVisible("CLOSED")).toBe(false);
  });

  it("CALCULATED round is not publicly visible", () => {
    expect(isRoundPubliclyVisible("CALCULATED")).toBe(false);
  });

  it("PUBLISHED round is publicly visible", () => {
    expect(isRoundPubliclyVisible("PUBLISHED")).toBe(true);
  });
});
