import { test, expect } from "@playwright/test";
import {
  clearAuthStorage,
  loginAsDemoUser,
  loginAsSupervisor,
} from "./fixtures/auth";
import { SUPERVISOR_PASSWORD } from "./fixtures/credentials";

test.describe("[E2E-PROFILE-USER-ONLY]", () => {
  test("[E2E-SUPERVISOR-NO-PROFILE] supervisor cannot stay on profile", async ({ page }) => {
    test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD not configured");

    await clearAuthStorage(page);
    await loginAsSupervisor(page);
    await page.waitForURL(/\/admin/, { timeout: 10_000 });

    await page.goto("/profile");
    await page.waitForURL(/\/admin/, { timeout: 10_000 });
    await expect(page.getByRole("heading", { name: "Личный кабинет" })).not.toBeVisible();
  });

  test("[E2E-USER-PROFILE-OK] demo user can access profile hub", async ({ page }) => {
    await clearAuthStorage(page);
    await loginAsDemoUser(page);

    await page.goto("/profile");
    await page.waitForURL(/\/profile/, { timeout: 10_000 });
    await expect(page.getByRole("heading", { name: "Личный кабинет" })).toBeVisible();
  });
});
