import { test, expect } from "@playwright/test";
import { clearAuthStorage, gotoProfile, loginAsUser, readToken } from "./fixtures/auth";
import { TOKEN_KEY } from "./fixtures/credentials";

test.describe("[E2E-401-LOGOUT]", () => {
  test("invalid token triggers auto logout on protected route", async ({ page }) => {
    await clearAuthStorage(page);
    await loginAsUser(page);
    await gotoProfile(page);

    await page.evaluate(
      ([key, value]) => localStorage.setItem(key, value),
      [TOKEN_KEY, "invalid.jwt.token"] as const,
    );

    await page.goto("/profile");
    await page.waitForURL("/");
    await expect(page.getByRole("button", { name: "Вход" })).toBeVisible({ timeout: 10_000 });
    expect(await readToken(page)).toBeNull();
  });
});
