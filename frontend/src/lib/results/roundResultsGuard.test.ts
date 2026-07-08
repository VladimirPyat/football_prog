import { describe, expect, it } from "vitest";
import { shouldFetchPublicResults } from "@/lib/results/roundResultsGuard";
import type { RoundStatus } from "@/types/api";

describe("roundResultsGuard", () => {
  it("shouldFetchPublicResults is true only for PUBLISHED", () => {
    const statuses: RoundStatus[] = ["DRAFT", "ACTIVE", "CLOSED", "CALCULATED", "PUBLISHED"];
    for (const status of statuses) {
      expect(shouldFetchPublicResults(status)).toBe(status === "PUBLISHED");
    }
  });
});
