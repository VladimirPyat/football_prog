import { test, expect } from "@playwright/test";
import { clearAuthStorage, gotoProfile, loginAsUser } from "./fixtures/auth";

test.describe("[E2E-USER-CONTESTS]", () => {
  test("authenticated user sees enrolled contests", async ({ page }) => {
    await clearAuthStorage(page);
    await loginAsUser(page);
    await gotoProfile(page);

    await page.goto("/contests");
    await expect(page.getByRole("heading", { name: "Конкурсы", level: 1 })).toBeVisible();
    const contestButton = page.getByRole("button").filter({ hasText: /E2E User Contest/i }).first();
    await expect(contestButton).toBeVisible();
    await contestButton.click();
    await page.waitForURL(/\/contest\/\d+/);
    await expect(page.getByRole("heading", { name: /Конкурс #\d+/ })).toBeVisible();
  });
});
