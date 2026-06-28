import { test, expect } from "@playwright/test";
import { loginAsDemoUser } from "./fixtures/auth";
import { fillAllMatchesDefault } from "./fixtures/predictionForm";
import { getRoundIdByNumber } from "./fixtures/predictionsApi";

test.describe("[E2E-DEADLINE-BLOCK]", () => {
  test("readonly after deadline passed", async ({ page }) => {
    const round9Id = await getRoundIdByNumber(1, 9);
    test.skip(!round9Id, "Round 9 not found");

    await loginAsDemoUser(page);
    await page.goto(`/contest/1/predict/${round9Id}`);

    await expect(page.getByText("Дедлайн прошёл")).toBeVisible({ timeout: 15_000 });
    const actionBtn = page.getByRole("button", { name: /Сохранить прогноз|Редактировать/ });
    await expect(actionBtn).toBeDisabled();
    await expect(page.locator('input[inputmode="numeric"]').first()).toBeDisabled();
  });
});
