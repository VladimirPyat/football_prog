import { test, expect } from "@playwright/test";
import {
  clearAuthStorage,
  loginAsSupervisor,
  loginOnStaffPage,
  openLoginModal,
} from "./fixtures/auth";
import { SUPERVISOR_LOGIN, SUPERVISOR_PASSWORD } from "./fixtures/credentials";

test.describe("Stage 2.1.2 supervisor UI fix smoke", () => {
  test.beforeEach(async ({ page }) => {
    await clearAuthStorage(page);
  });

  test("[UI-PARAM-RULES] parameters shows scoring labels", async ({ page }) => {
    test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD missing");

    await loginAsSupervisor(page);
    await page.goto("/admin/settings/parameters");
    await expect(page.getByText("За точный счёт")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("Бонус 1")).toBeVisible();
    await expect(page.getByText("Основные очки")).toBeVisible();
  });

  test("[UI-PARAM-LIFE] RUNNING contest shows pause control", async ({ page }) => {
    test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD missing");

    await loginAsSupervisor(page);
    await page.goto("/admin/settings/parameters");
    await expect(page.getByRole("button", { name: "Остановить конкурс" })).toBeVisible({
      timeout: 15_000,
    });
  });

  test("[UI-LOGIN-RESET] forgot password checkbox reveals email field", async ({ page }) => {
    await page.goto("/");
    await openLoginModal(page);
    await expect(page.getByLabel("Забыли пароль?")).not.toBeChecked();
    await page.getByLabel("Забыли пароль?").check();
    await expect(page.getByLabel("Email, указанный при регистрации")).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Отправить ссылку для восстановления" }),
    ).toBeVisible();
  });

  test("[UI-LOGIN-RESET] staff login forgot password checkbox", async ({ page }) => {
    await page.goto("/staff/login");
    await page.getByLabel("Забыли пароль?").check();
    await expect(page.getByLabel("Email, указанный при регистрации")).toBeVisible();
  });

  test("[UI-ROUNDS-SIDEBAR] rounds page shows status sidebar", async ({ page }) => {
    test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD missing");

    await loginAsSupervisor(page);
    await page.goto("/admin/rounds");
    await expect(page.getByText("Статус тура")).toBeVisible({ timeout: 15_000 });
  });

  test("[UI-TEAMS-LOGO] teams page loads logo from API host", async ({ page }) => {
    test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD missing");

    await loginAsSupervisor(page);
    const logoReq = page.waitForResponse(
      (res) =>
        res.url().includes("/static/assets/default-team-logo") && res.status() === 200,
      { timeout: 15_000 },
    );
    await page.goto("/admin/settings/teams");
    await logoReq;
    await expect(page.locator('img[src*="/static/assets/default-team-logo"]').first()).toBeVisible();
  });
});
