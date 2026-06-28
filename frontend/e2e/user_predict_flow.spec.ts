import { test, expect } from "@playwright/test";
import { loginAsDemoUser, gotoProfile } from "./fixtures/auth";
import { fillAllMatchesDefault, ensurePredictionEditing } from "./fixtures/predictionForm";
import { ensureE2eActiveRound } from "./fixtures/predictionsApi";

test.describe("[E2E-USER-PREDICT-FLOW]", () => {
  test("profile link → predict → save → edit → save", async ({ page }) => {
    await ensureE2eActiveRound(1);
    await loginAsDemoUser(page);
    await gotoProfile(page);

    const predictLink = page.getByRole("link", { name: "Сделать прогноз" });
    const hasActiveRound = await predictLink.isVisible();
    test.skip(!hasActiveRound, "No active round predict link");

    await predictLink.click();
    await expect(page).toHaveURL(/\/contest\/\d+\/predict\/\d+/);

    await ensurePredictionEditing(page);
    await fillAllMatchesDefault(page, 8);
    await page.getByRole("button", { name: "Сохранить прогноз" }).click();
    await expect(page.getByRole("button", { name: "Редактировать" })).toBeVisible({
      timeout: 10_000,
    });

    await page.getByRole("button", { name: "Редактировать" }).click();
    const firstInput = page.locator('input[inputmode="numeric"]').first();
    await firstInput.fill("3");
    await page.getByRole("button", { name: "Сохранить прогноз" }).click();
    await expect(page.getByRole("button", { name: "Редактировать" })).toBeVisible({
      timeout: 10_000,
    });

    await page.reload();
    await expect(page.getByRole("button", { name: "Редактировать" })).toBeVisible({
      timeout: 10_000,
    });
  });
});
