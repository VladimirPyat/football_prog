import { describe, expect, it } from "vitest";
import { shouldShowDeadlineWarning } from "./deadlineWarning";

describe("shouldShowDeadlineWarning", () => {
  it("[UNIT-DEADLINE-WARN] true when 3600 seconds left", () => {
    expect(shouldShowDeadlineWarning(3600)).toBe(true);
  });

  it("[UNIT-DEADLINE-WARN] false when 86401 seconds left", () => {
    expect(shouldShowDeadlineWarning(86401)).toBe(false);
  });

  it("[UNIT-DEADLINE-WARN] false when 0", () => {
    expect(shouldShowDeadlineWarning(0)).toBe(false);
  });
});
