import { test, expect } from "@playwright/test";
import { clearAuthStorage } from "./fixtures/auth";
import { getRoundIdByNumber } from "./fixtures/predictionsApi";

test.describe("[E2E-RESULTS-UNAVAILABLE]", () => {
  test("non-published round shows unavailable stub", async ({ page }) => {
    const round10Id = await getRoundIdByNumber(1, 10);
    test.skip(!round10Id, "Round 10 not found");

    await clearAuthStorage(page);
    await page.goto("/contest/1");
    await page.getByRole("tab", { name: "Результаты" }).click();
    await page.locator("#round-select").selectOption(String(round10Id));

    await expect(page.getByTestId("results-unavailable")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("results-matrix")).not.toBeVisible();
  });
});

test.describe("[E2E-RESULTS-MATRIX]", () => {
  test("published round shows results matrix with points", async ({ page }) => {
    const round9Id = await getRoundIdByNumber(1, 9);
    test.skip(!round9Id, "Round 9 not found");

    await clearAuthStorage(page);
    await page.goto("/contest/1");
    await page.getByRole("tab", { name: "Результаты" }).click();
    await page.locator("#round-select").selectOption(String(round9Id));

    const matrix = page.getByTestId("results-matrix");
    await expect(matrix).toBeVisible({ timeout: 15_000 });
    await expect(matrix.locator("tbody tr").first()).toBeVisible();
  });
});
