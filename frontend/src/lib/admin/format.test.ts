import { describe, it, expect, vi, afterEach } from "vitest";
import { matchPhaseLabel, roundStatusHint } from "@/lib/admin/format";

describe("matchPhaseLabel", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("[UNIT-MATCH-PHASE-LABEL] CLOSED + SCHEDULED + kickoff passed → «Идёт»", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-06-27T15:00:00Z"));
    expect(matchPhaseLabel("SCHEDULED", "2026-06-27T14:00:00Z", "CLOSED")).toBe("Идёт");
  });

  it("[UNIT-MATCH-PHASE-LABEL] CLOSED + SCHEDULED + kickoff future → «Запланирован»", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-06-27T12:00:00Z"));
    expect(matchPhaseLabel("SCHEDULED", "2026-06-27T14:00:00Z", "CLOSED")).toBe("Запланирован");
  });

  it("[UNIT-MATCH-PHASE-LABEL] CLOSED + FINISHED → «Завершён»", () => {
    expect(matchPhaseLabel("FINISHED", "2026-06-27T14:00:00Z", "CLOSED")).toBe("Завершён");
  });

  it("[UNIT-MATCH-PHASE-LABEL] CALCULATED round delegates to matchStatusLabel", () => {
    expect(matchPhaseLabel("SCHEDULED", "2026-06-27T14:00:00Z", "CALCULATED")).toBe("Запланирован");
    expect(matchPhaseLabel("SCHEDULED", "2020-01-01T12:00:00Z", "CALCULATED")).toBe("Запланирован");
  });
});

describe("roundStatusHint", () => {
  it("[UNIT-LIFECYCLE-HINTS] CLOSED mentions kickoff, Результаты, Рассчитать", () => {
    const hint = roundStatusHint("CLOSED");
    expect(hint).toMatch(/начала матча/i);
    expect(hint).toMatch(/Результаты/);
    expect(hint).toMatch(/Рассчитать/);
  });

  it("[UNIT-LIFECYCLE-HINTS] CALCULATED mentions проверка очков and Опубликовать", () => {
    const hint = roundStatusHint("CALCULATED");
    expect(hint).toMatch(/Очки посчитаны|провер/i);
    expect(hint).toMatch(/Опубликовать/);
  });
});
