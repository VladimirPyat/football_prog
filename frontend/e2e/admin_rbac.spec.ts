import { test, expect } from "@playwright/test";
import { clearAuthStorage, loginAsDemoUser } from "./fixtures/auth";
import { seedSupervisorSession, waitForAdminShell } from "./fixtures/adminApi";
import { SUPERVISOR_PASSWORD } from "./fixtures/credentials";

test.describe("[E2E-ADMIN-RBAC]", () => {
  test("visitor cannot access admin settings", async ({ page }) => {
    await clearAuthStorage(page);
    await page.goto("/admin/settings/parameters");
    await expect(page.getByRole("button", { name: "Сохранить параметры" })).not.toBeVisible({
      timeout: 15_000,
    });
  });

  test("USER role blocked from admin rounds", async ({ page }) => {
    await clearAuthStorage(page);
    await loginAsDemoUser(page);
    await page.goto("/admin/rounds");
    await page.waitForURL((url) => !url.pathname.startsWith("/admin/rounds"), {
      timeout: 15_000,
    });
    await expect(page.getByRole("link", { name: "Туры" })).not.toBeVisible();
  });

  test("supervisor sees admin nav tabs", async ({ page }) => {
    test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD not configured");

    await clearAuthStorage(page);
    await seedSupervisorSession(page);
    await page.goto("/admin/settings/parameters");
    await page.waitForLoadState("networkidle");
    await waitForAdminShell(page);
    await expect(page.getByRole("link", { name: "Настройки" })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByRole("link", { name: "Туры" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Рассылки" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Результаты" })).toBeVisible();
  });

  test("[E2E-ADMIN-NEWSLETTERS-PLACEHOLDER] newsletters tab shows Stage 3 placeholder", async ({
    page,
  }) => {
    test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD not configured");

    await clearAuthStorage(page);
    await seedSupervisorSession(page);
    await page.goto("/admin/newsletters");
    await page.waitForLoadState("networkidle");
    await waitForAdminShell(page);
    await expect(page.getByText(/Stage 3/i)).toBeVisible();
    await expect(page.getByText("Создание и отправка писем пока недоступны")).toBeVisible();
  });
});
