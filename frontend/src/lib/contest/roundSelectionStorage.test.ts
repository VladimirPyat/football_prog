import { describe, expect, it, beforeEach, vi } from "vitest";
import {
  getStoredRoundId,
  resolveRoundId,
  roundSelectionKey,
  setStoredRoundId,
} from "@/lib/contest/roundSelectionStorage";
import { pickDefaultRound } from "@/lib/contest/pickDefaultRound";
import type { RoundOut } from "@/types/api";

function round(id: number, status: RoundOut["status"] = "PUBLISHED"): RoundOut {
  return {
    id,
    number: id,
    status,
    deadline: "2026-01-01T12:00:00Z",
    contest_id: 1,
    matches_count: 4,
    kind: "REGULAR",
    supplementary_index: null,
    source_round_numbers: [],
  };
}

describe("roundSelectionStorage", () => {
  beforeEach(() => {
    const store: Record<string, string> = {};
    vi.stubGlobal("localStorage", {
      getItem(key: string) {
        return store[key] ?? null;
      },
      setItem(key: string, value: string) {
        store[key] = value;
      },
      removeItem(key: string) {
        delete store[key];
      },
    });
  });

  it("builds scoped storage key", () => {
    expect(roundSelectionKey(42, "contest-public")).toBe("fp_selected_round:42:contest-public");
  });

  it("persists and reads round id", () => {
    setStoredRoundId(1, "admin-rounds", 7);
    expect(getStoredRoundId(1, "admin-rounds")).toBe(7);
  });

  it("resolveRoundId prefers stored when valid", () => {
    const rounds = [round(1), round(2)];
    expect(resolveRoundId(rounds, 2, () => 1)).toBe(2);
  });

  it("resolveRoundId falls back when stored invalid", () => {
    const rounds = [round(1), round(2)];
    expect(resolveRoundId(rounds, 99, () => 1)).toBe(1);
  });
});

describe("pickDefaultRound", () => {
  it("predictions tab prefers ACTIVE", () => {
    const rounds = [round(1, "PUBLISHED"), round(2, "ACTIVE")];
    expect(pickDefaultRound(rounds, "predictions")).toBe(2);
  });

  it("leaderboard tab prefers last published", () => {
    const rounds = [round(1, "ACTIVE"), round(2, "PUBLISHED")];
    expect(pickDefaultRound(rounds, "leaderboard")).toBe(2);
  });
});
