import { describe, expect, it } from "vitest";
import { formatRoundOptionLabel, formatRoundTitle } from "@/lib/admin/roundLabel";
import type { RoundOut } from "@/types/api";

const baseRound: RoundOut = {
  id: 1,
  contest_id: 1,
  number: 2,
  deadline: "2026-01-01T12:00:00Z",
  status: "DRAFT",
  matches_count: 1,
  kind: "REGULAR",
  supplementary_index: null,
  source_round_numbers: [],
};

describe("formatRoundTitle", () => {
  it("shows regular tour number", () => {
    expect(formatRoundTitle(baseRound)).toBe("Тур 2");
  });

  it("shows supplementary tour with single source", () => {
    expect(
      formatRoundTitle({
        ...baseRound,
        kind: "SUPPLEMENTARY",
        supplementary_index: 1,
        source_round_numbers: [1],
      }),
    ).toBe("ДопТур1 (из тура 1)");
  });

  it("shows supplementary tour with multiple sources", () => {
    expect(
      formatRoundTitle({
        ...baseRound,
        kind: "SUPPLEMENTARY",
        supplementary_index: 2,
        source_round_numbers: [3, 1],
      }),
    ).toBe("ДопТур2 (из туров 1, 3)");
  });
});

describe("formatRoundOptionLabel", () => {
  it("appends status label", () => {
    expect(formatRoundOptionLabel(baseRound)).toBe("Тур 2 — Черновик");
  });
});
