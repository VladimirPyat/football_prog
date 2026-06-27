import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { resolveAssetUrl } from "@/lib/api/resolveAssetUrl";

describe("resolveAssetUrl", () => {
  const prev = process.env.NEXT_PUBLIC_API_URL;

  beforeEach(() => {
    process.env.NEXT_PUBLIC_API_URL = "http://127.0.0.1:8000";
  });

  afterEach(() => {
    process.env.NEXT_PUBLIC_API_URL = prev;
  });

  it("prefixes /static/ paths with NEXT_PUBLIC_API_URL", () => {
    expect(resolveAssetUrl("/static/assets/default-team-logo.jpg")).toBe(
      "http://127.0.0.1:8000/static/assets/default-team-logo.jpg",
    );
  });

  it("leaves absolute URLs unchanged", () => {
    expect(resolveAssetUrl("https://cdn.example/logo.png")).toBe("https://cdn.example/logo.png");
  });
});
