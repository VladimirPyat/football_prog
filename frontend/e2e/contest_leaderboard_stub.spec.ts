import { test, expect } from "@playwright/test";
import { loginAsDemoUser } from "./fixtures/auth";
import { getRoundIdByNumber, ensureE2eActiveRound } from "./fixtures/predictionsApi";

test.describe("[E2E-LB-MOCK-DISPLAY]", () => {
  test("leaderboard shows mock table for any round", async ({ page }) => {
    await ensureE2eActiveRound(1);
    const round10Id = await getRoundIdByNumber(1, 10);
    test.skip(!round10Id, "Round 10 not found");

    await loginAsDemoUser(page);
    await page.goto("/contest/1");
    await expect(page.getByRole("tab", { name: "Лидерборд" })).toBeVisible({ timeout: 15_000 });
    await page.getByRole("tab", { name: "Лидерборд" }).click();
    await expect(page.getByTestId("round-selector")).toBeVisible({ timeout: 15_000 });
    await page.locator("#round-select").selectOption(String(round10Id));

    await expect(page.getByTestId("leaderboard-table")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Сидоров С.С.")).toBeVisible();
  });
});
