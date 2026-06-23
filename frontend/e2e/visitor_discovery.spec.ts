import { test, expect } from "@playwright/test";
import { clearAuthStorage } from "./fixtures/auth";
import { API_BASE } from "./fixtures/credentials";

test.describe("[E2E-VISITOR-DISCOVERY]", () => {
  test("visitor sees public contests and can open contest page", async ({ page }) => {
    const apiRes = await fetch(`${API_BASE}/api/v1/contests/public`);
    expect(apiRes.ok).toBe(true);
    const publicContests = (await apiRes.json()) as Array<{ id: number; status: string }>;
    expect(publicContests.length).toBeGreaterThan(0);
    expect(publicContests.every((c) => c.status === "RUNNING")).toBe(true);

    await clearAuthStorage(page);
    await page.goto("/");

    await expect(page.getByRole("heading", { name: "Конкурс спортивных прогнозов" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Активные конкурсы" })).toBeVisible();
    await expect(page.getByRole("button", { name: /Default/i })).toBeVisible();

    await page.getByRole("button", { name: /Default/i }).click();
    await page.waitForURL(/\/contest\/\d+/);
    await expect(page.getByRole("heading", { name: /Конкурс #\d+/ })).toBeVisible();
  });
});
