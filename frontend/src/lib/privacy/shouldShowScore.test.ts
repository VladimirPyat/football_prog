import { describe, expect, it } from "vitest";
import { shouldShowScore } from "./shouldShowScore";

const entryOwn = { user_id: 1, predictions: [{ match_id: 1 }] };
const entryOther = { user_id: 2, predictions: null };
const entryOtherVisible = { user_id: 2, predictions: [{ match_id: 1 }] };
const viewer = { id: 1, role: "USER" as const };
const admin = { id: 99, role: "ADMIN" as const };

describe("shouldShowScore", () => {
  it("[UNIT-PRIVACY-SHOW] pre-deadline: own scores visible", () => {
    expect(shouldShowScore(entryOwn, viewer, false)).toBe(true);
  });

  it("[UNIT-PRIVACY-SHOW] pre-deadline: other hidden", () => {
    expect(shouldShowScore(entryOther, viewer, false)).toBe(false);
  });

  it("[UNIT-PRIVACY-SHOW] pre-deadline: ADMIN sees all", () => {
    expect(shouldShowScore(entryOther, admin, false)).toBe(false);
    expect(shouldShowScore({ user_id: 2, predictions: [{ match_id: 1 }] }, admin, false)).toBe(
      true,
    );
  });

  it("[UNIT-PRIVACY-SHOW] post-deadline: all with data", () => {
    expect(shouldShowScore(entryOtherVisible, viewer, true)).toBe(true);
  });

  it("[UNIT-PRIVACY-SHOW] visitor null pre-deadline", () => {
    expect(shouldShowScore(entryOwn, null, false)).toBe(false);
  });

  it("[UNIT-PRIVACY-VISITOR-POST] visitor post-deadline sees scores", () => {
    expect(shouldShowScore(entryOtherVisible, null, true)).toBe(true);
  });
});
