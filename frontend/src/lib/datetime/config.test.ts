import { describe, expect, it, afterEach, vi } from "vitest";
import {
  getApiStorageTimeZone,
  getDateTimeLocale,
  getDisplayTimeZone,
} from "@/lib/datetime/config";

describe("datetime config", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("defaults API storage to UTC", () => {
    vi.unstubAllEnvs();
    expect(getApiStorageTimeZone()).toBe("UTC");
  });

  it("reads display timezone from env", () => {
    vi.stubEnv("NEXT_PUBLIC_DISPLAY_TIMEZONE", "Europe/Moscow");
    expect(getDisplayTimeZone()).toBe("Europe/Moscow");
  });

  it("display timezone unset → undefined (browser local)", () => {
    vi.unstubAllEnvs();
    expect(getDisplayTimeZone()).toBeUndefined();
  });

  it("defaults datetime locale to ru-RU", () => {
    expect(getDateTimeLocale()).toBe("ru-RU");
  });
});
