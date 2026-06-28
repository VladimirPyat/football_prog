import { test, expect } from "@playwright/test";
import { loginAsDemoUser } from "./fixtures/auth";
import { ensurePredictionEditing, fillAllMatchesDefault, clearAllScores } from "./fixtures/predictionForm";
import { ensureE2eActiveRound, getActiveRoundId, getContestMaxScore } from "./fixtures/predictionsApi";

test.describe("[E2E-PRED-VALIDATION]", () => {
  test("rejects invalid input, accepts valid batch including 0", async ({ page }) => {
    await ensureE2eActiveRound(1);
    const roundId = await getActiveRoundId(1);
    const maxScore = await getContestMaxScore(1);
    test.skip(!roundId, "No ACTIVE round");

    await loginAsDemoUser(page);
    await page.goto(`/contest/1/predict/${roundId}`);
    await ensurePredictionEditing(page);
    await clearAllScores(page);

    const saveBtn = page.getByRole("button", { name: "Сохранить прогноз" });
    const firstInput = page.locator('input[inputmode="numeric"]').first();

    await firstInput.fill("abc");
    await expect(firstInput).toHaveValue("");
    await expect(saveBtn).toBeDisabled();

    await fillAllMatchesDefault(page, 7);
    const overInput = page.locator('input[inputmode="numeric"]').nth(14);
    await overInput.fill(String(maxScore + 1));
    await expect(saveBtn).toBeDisabled();

    await fillAllMatchesDefault(page, 8);
    await fillAllMatchesDefault(page, 8);
    const zeroInputs = page.locator('input[inputmode="numeric"]');
    await zeroInputs.nth(0).fill("0");
    await zeroInputs.nth(1).fill("0");

    await expect(saveBtn).toBeEnabled();
    await saveBtn.click();
    await expect(page.getByRole("button", { name: "Редактировать" })).toBeVisible({
      timeout: 10_000,
    });
  });
});
