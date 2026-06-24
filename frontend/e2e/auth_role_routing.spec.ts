import { test, expect } from "@playwright/test";
import {
  clearAuthStorage,
  loginAsAdmin,
  loginAsDemoUser,
  loginAsSupervisor,
} from "./fixtures/auth";
import { ADMIN_PASSWORD, SUPERVISOR_PASSWORD } from "./fixtures/credentials";

test.describe("[E2E-ROLE-ROUTING]", () => {
  test("[E2E-USER-LOGIN-PROFILE] demo user lands on profile, not admin", async ({ page }) => {
    await clearAuthStorage(page);
    await loginAsDemoUser(page);

    await page.waitForURL(/\/profile/, { timeout: 10_000 });
    await expect(page.getByRole("heading", { name: "Личный кабинет" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Управление", exact: true })).not.toBeVisible();
    expect(page.url()).not.toMatch(/\/admin/);
  });

  test("[E2E-SUPERVISOR-LOGIN-ADMIN] supervisor lands on admin area, not profile", async ({
    page,
  }) => {
    test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD not configured");

    await clearAuthStorage(page);
    await loginAsSupervisor(page);

    await page.waitForURL(/\/admin(\/|$)/, { timeout: 10_000 });
    expect(page.url()).not.toMatch(/\/profile/);
    await expect(page.getByRole("link", { name: "Личный кабинет" })).not.toBeVisible();
  });

  test("[E2E-ADMIN-LOGIN-ADMIN] admin sees stub dashboard", async ({ page }) => {
    test.skip(!ADMIN_PASSWORD, "SEED_ADMIN_PASSWORD not configured");

    await clearAuthStorage(page);
    await loginAsAdmin(page);

    await page.waitForURL(/\/admin\/?(\?.*)?$/, { timeout: 10_000 });
    await expect(page.getByRole("heading", { name: "Панель администратора" })).toBeVisible();
    await expect(page.getByText(/Скоро — этап 2\.3/).first()).toBeVisible();
  });

  test("[E2E-HOME-USER] authenticated user on home goes to participant flow", async ({
    page,
  }) => {
    await clearAuthStorage(page);
    await loginAsDemoUser(page);
    await page.waitForURL(/\/profile/, { timeout: 10_000 });

    await page.goto("/");
    await page.waitForURL(/\/(contests|contest\/\d+)/, { timeout: 10_000 });
    expect(page.url()).not.toMatch(/\/admin/);
  });

  test("[E2E-HOME-STAFF] authenticated supervisor on home goes to admin", async ({ page }) => {
    test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD not configured");

    await clearAuthStorage(page);
    await loginAsSupervisor(page);
    await page.waitForURL(/\/admin/, { timeout: 10_000 });

    await page.goto("/");
    await page.waitForURL(/\/admin/, { timeout: 10_000 });
  });
});
