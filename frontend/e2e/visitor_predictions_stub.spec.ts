import { test, expect } from "@playwright/test";
import { clearAuthStorage } from "./fixtures/auth";
import { ensureE2eActiveRound, getActiveRoundId } from "./fixtures/predictionsApi";

test.describe("[E2E-VISITOR-PRED-STUB]", () => {
  test("visitor sees stub before deadline on active round", async ({ page }) => {
    await ensureE2eActiveRound(1);
    const activeRoundId = await getActiveRoundId(1);
    test.skip(!activeRoundId, "No ACTIVE round after dev_setup --e2e-with-published");

    await clearAuthStorage(page);
    await page.goto("/contest/1");
    await expect(page.getByRole("button", { name: "Вход" })).toBeVisible({ timeout: 10_000 });

    const roundSelect = page.locator("#round-select");
    if (await roundSelect.isVisible()) {
      await roundSelect.selectOption(String(activeRoundId));
    }

    await expect(page.getByText("Будет доступно после дедлайна")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("predictions-matrix")).not.toBeVisible();
  });
});
