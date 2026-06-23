import { describe, it, expect, afterEach } from "vitest";
import { resolveDefaultContestId } from "@/lib/contest/resolveDefaultContestId";

describe("resolveDefaultContestId", () => {
  const original = process.env.NEXT_PUBLIC_DEFAULT_CONTEST_ID;

  afterEach(() => {
    if (original === undefined) {
      delete process.env.NEXT_PUBLIC_DEFAULT_CONTEST_ID;
    } else {
      process.env.NEXT_PUBLIC_DEFAULT_CONTEST_ID = original;
    }
  });

  it("returns valid env integer", () => {
    process.env.NEXT_PUBLIC_DEFAULT_CONTEST_ID = "42";
    expect(resolveDefaultContestId()).toBe(42);
  });

  it("defaults to 1 when env unset", () => {
    delete process.env.NEXT_PUBLIC_DEFAULT_CONTEST_ID;
    expect(resolveDefaultContestId()).toBe(1);
  });

  it("throws on invalid env", () => {
    process.env.NEXT_PUBLIC_DEFAULT_CONTEST_ID = "abc";
    expect(() => resolveDefaultContestId()).toThrow("Invalid NEXT_PUBLIC_DEFAULT_CONTEST_ID");
  });

  it("throws on zero or negative", () => {
    process.env.NEXT_PUBLIC_DEFAULT_CONTEST_ID = "0";
    expect(() => resolveDefaultContestId()).toThrow("Invalid NEXT_PUBLIC_DEFAULT_CONTEST_ID");
  });
});
