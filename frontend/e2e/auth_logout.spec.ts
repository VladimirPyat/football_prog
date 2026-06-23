import { test, expect } from "@playwright/test";
import { clearAuthStorage, gotoProfile, loginAsUser, readToken } from "./fixtures/auth";

test.describe("[E2E-LOGOUT]", () => {
  test("logout clears token and returns visitor state", async ({ page }) => {
    await clearAuthStorage(page);
    await loginAsUser(page);
    await gotoProfile(page);

    await page.locator("header").getByRole("button", { name: "Выйти" }).click();
    await page.waitForURL("/");
    await expect(page.getByRole("button", { name: "Вход" })).toBeVisible();
    expect(await readToken(page)).toBeNull();
  });
});
