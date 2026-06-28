import { describe, expect, it } from "vitest";
import { buildPredictionBatch, countFilledMatches, predictionBatchSchema } from "./prediction";

describe("predictionBatchSchema", () => {
  const maxScore = 15;
  const matchCount = 8;

  it("[UNIT-BATCH-SCHEMA] rejects 7 of 8 matches", () => {
    const predictions = Array.from({ length: 7 }, (_, i) => ({
      match_id: i + 1,
      score1: 1,
      score2: 0,
    }));
    const r = predictionBatchSchema(maxScore, matchCount).safeParse({ predictions });
    expect(r.success).toBe(false);
  });

  it("[UNIT-BATCH-SCHEMA] accepts 8 of 8 matches", () => {
    const predictions = Array.from({ length: 8 }, (_, i) => ({
      match_id: i + 1,
      score1: 2,
      score2: 1,
    }));
    const r = predictionBatchSchema(maxScore, matchCount).safeParse({ predictions });
    expect(r.success).toBe(true);
  });

  it("[UNIT-BATCH-SCHEMA] respects dynamic maxScore", () => {
    const predictions = Array.from({ length: 8 }, (_, i) => ({
      match_id: i + 1,
      score1: maxScore + 1,
      score2: 0,
    }));
    const r = predictionBatchSchema(maxScore, matchCount).safeParse({ predictions });
    expect(r.success).toBe(false);
  });

  it("[UNIT-BATCH-SCHEMA] partial form with undefined scores does not serialize as 0", () => {
    const form = {
      1: { score1: 1, score2: 2 },
      2: { score1: undefined, score2: undefined },
      3: { score1: 0, score2: 0 },
    };
    const batch = buildPredictionBatch(form, [1, 2, 3]);
    expect(batch).toHaveLength(2);
    expect(batch.find((b) => b.match_id === 2)).toBeUndefined();
    expect(countFilledMatches(form, [1, 2, 3])).toBe(2);
  });
});
