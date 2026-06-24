import { test, expect } from "@playwright/test";
import { clearAuthStorage, loginOnStaffPage } from "./fixtures/auth";
import { SUPERVISOR_LOGIN, SUPERVISOR_PASSWORD } from "./fixtures/credentials";

test.describe("[E2E-STAFF-LOGIN]", () => {
  test("[E2E-STAFF-LOGIN-PAGE] staff login page redirects supervisor to admin", async ({
    page,
  }) => {
    test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD not configured");

    await clearAuthStorage(page);
    await loginOnStaffPage(page, SUPERVISOR_LOGIN, SUPERVISOR_PASSWORD);

    await page.waitForURL(/\/admin/, { timeout: 10_000 });
    expect(page.url()).not.toMatch(/\/profile/);
    await expect(page.getByRole("link", { name: "Управление", exact: true })).toBeVisible();
  });
});
