import { test, expect } from "@playwright/test";
import { clearAuthStorage } from "./fixtures/auth";
import { getRoundIdByNumber } from "./fixtures/predictionsApi";

test.describe("[E2E-VISITOR-PRED-PUBLIC]", () => {
  test("visitor sees full matrix after deadline without login", async ({ page }) => {
    const round9Id = await getRoundIdByNumber(1, 9);
    test.skip(!round9Id, "Round 9 not found in contest 1");

    await clearAuthStorage(page);
    await page.goto("/contest/1");
    await expect(page.getByRole("button", { name: "Вход" })).toBeVisible({ timeout: 10_000 });

    await page.locator("#round-select").selectOption(String(round9Id));

    await expect(page.getByTestId("predictions-matrix")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("Войдите, чтобы просмотреть прогнозы")).not.toBeVisible();
    await expect(page.locator("[data-testid='prediction-score']").first()).toBeVisible();
  });
});
