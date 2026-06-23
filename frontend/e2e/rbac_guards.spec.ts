import { test, expect } from "@playwright/test";
import { clearAuthStorage, gotoProfile, loginAsUser } from "./fixtures/auth";

test.describe("[E2E-RBAC-GUARDS]", () => {
  test("visitor cannot access protected routes", async ({ page }) => {
    await clearAuthStorage(page);

    await page.goto("/profile");
    await page.waitForURL("/");
    await expect(page.getByRole("heading", { name: "Личный кабинет" })).not.toBeVisible();

    await page.goto("/contests");
    await page.waitForURL("/");
    await expect(page.getByRole("heading", { name: "Конкурсы", exact: true })).not.toBeVisible();
  });

  test("authenticated user can access profile", async ({ page }) => {
    await clearAuthStorage(page);
    await loginAsUser(page);
    await gotoProfile(page);
    await expect(page.getByRole("heading", { name: "Личный кабинет" })).toBeVisible();
  });
});
