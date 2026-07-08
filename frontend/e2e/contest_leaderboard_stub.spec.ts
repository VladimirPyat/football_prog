import { test, expect } from "@playwright/test";
import { clearAuthStorage } from "./fixtures/auth";
import { getRoundIdByNumber } from "./fixtures/predictionsApi";

test.describe("[E2E-LB-VISITOR]", () => {
  test.use({ viewport: { width: 1280, height: 720 } });

  test("visitor sees real leaderboard on published round", async ({ page }) => {
    const round9Id = await getRoundIdByNumber(1, 9);
    test.skip(!round9Id, "Round 9 not found");

    await clearAuthStorage(page);
    await page.goto("/contest/1");
    await expect(page.getByRole("button", { name: "Вход" })).toBeVisible({ timeout: 15_000 });

    await page.getByRole("tab", { name: "Лидерборд" }).click();
    await expect(page.getByTestId("round-selector")).toBeVisible({ timeout: 15_000 });
    await page.locator("#round-select").selectOption(String(round9Id));

    const table = page.getByTestId("leaderboard-table");
    await expect(table).toBeVisible({ timeout: 15_000 });
    await expect(table.locator("tbody tr").first()).toBeVisible();
    await expect(table.getByText("Место")).toBeVisible();
    await expect(table.getByText("очков")).toBeVisible();
  });
});

test.describe("[E2E-LB-B4-COLUMNS]", () => {
  test.use({ viewport: { width: 1280, height: 720 } });

  test("desktop shows B4 count columns on published round", async ({ page }) => {
    const round9Id = await getRoundIdByNumber(1, 9);
    test.skip(!round9Id, "Round 9 not found");

    await clearAuthStorage(page);
    await page.goto("/contest/1");
    await page.getByRole("tab", { name: "Лидерборд" }).click();
    await page.locator("#round-select").selectOption(String(round9Id));

    const table = page.getByTestId("leaderboard-table");
    await expect(table).toBeVisible({ timeout: 15_000 });
    await expect(table.getByText("Точный", { exact: true }).first()).toBeVisible();
    await expect(table.getByText("ИТОГО", { exact: true }).first()).toBeVisible();
    await expect(table.getByText("Ларин").first()).toBeVisible({ timeout: 15_000 });
  });
});
