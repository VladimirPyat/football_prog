import { test, expect } from "@playwright/test";
import { loginAsDemoUser } from "./fixtures/auth";

import { getRoundIdByNumber, ensureE2eActiveRound } from "./fixtures/predictionsApi";

test.describe("[E2E-CONTEST-PRED-TAB]", () => {
  test("predictions tab with round selector", async ({ page }) => {
    await ensureE2eActiveRound(1);
    const round9Id = await getRoundIdByNumber(1, 9);
    test.skip(!round9Id, "Round 9 not found");

    await loginAsDemoUser(page);
    await page.goto("/contest/1");

    await expect(page.getByTestId("round-selector")).toBeVisible();
    await page.getByRole("tab", { name: "Прогнозы" }).click();
    await expect(page.getByTestId("predictions-matrix")).toBeVisible({ timeout: 15_000 });

    await page.locator("#round-select").selectOption(String(round9Id));
    await expect(page.getByTestId("predictions-matrix")).toBeVisible({ timeout: 15_000 });

    await page.getByRole("tab", { name: "Лидерборд" }).click();
    await page.getByRole("tab", { name: "Прогнозы" }).click();
    await expect(page.getByTestId("predictions-matrix")).toBeVisible({ timeout: 15_000 });
  });
});
