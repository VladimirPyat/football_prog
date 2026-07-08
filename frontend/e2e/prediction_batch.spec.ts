import { test, expect } from "@playwright/test";
import { loginAsDemoUser } from "./fixtures/auth";
import { fillAllMatchesDefault, fillMatchScores, ensurePredictionEditing, clearAllScores } from "./fixtures/predictionForm";
import { ensureE2eActiveRound, getActiveRoundId } from "./fixtures/predictionsApi";

test.describe("[E2E-PRED-BATCH]", () => {
  test("7/8 disabled, 8/8 enabled, score 0 valid, save persists", async ({ page }) => {
    await ensureE2eActiveRound(1);
    const roundId = await getActiveRoundId(1);
    test.skip(!roundId, "No ACTIVE round — run dev_setup.py --ensure-running-only --e2e-with-published");

    await loginAsDemoUser(page);
    await page.goto(`/contest/1/predict/${roundId}`);
    await ensurePredictionEditing(page);
    await clearAllScores(page);

    const saveBtn = page.getByRole("button", { name: "Сохранить прогноз" });
    await expect(saveBtn).toBeDisabled();

    const scores7 = Array.from({ length: 7 }, (_, i) => ({
      score1: (i % 3) + 1,
      score2: i % 2,
    }));
    await fillMatchScores(page, scores7);
    await expect(saveBtn).toBeDisabled();

    await fillMatchScores(page, [...scores7, { score1: 0, score2: 0 }]);
    await expect(saveBtn).toBeEnabled();

    await saveBtn.click();
    await expect(page.getByRole("button", { name: "Редактировать" })).toBeVisible({
      timeout: 10_000,
    });

    await page.reload();
    await expect(page.getByRole("button", { name: "Редактировать" })).toBeVisible({
      timeout: 10_000,
    });
  });
});
