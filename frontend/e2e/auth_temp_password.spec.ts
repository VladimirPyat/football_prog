import { test, expect } from "@playwright/test";
import {
  clearAuthStorage,
  fillLoginForm,
  inviteTempUser,
  openLoginModal,
  submitLogin,
} from "./fixtures/auth";
import { SUPERVISOR_PASSWORD } from "./fixtures/credentials";

test.describe("[E2E-TEMP-PASSWORD]", () => {
  test.skip(!SUPERVISOR_PASSWORD, "[SKIP-NO-TEMP-USER] SEED_SUPERVISOR_PASSWORD not configured");

  test("temp password user must change password before profile", async ({ page }) => {
    const invited = await inviteTempUser();
    const newPassword = "NewSecure1!";

    await clearAuthStorage(page);
    await openLoginModal(page);
    await fillLoginForm(page, invited.login, invited.tempPassword);
    await submitLogin(page);

    await page.waitForURL(/\/change-password/);
    await expect(page.getByRole("heading", { name: "Смена пароля" })).toBeVisible();

    await page.goto("/profile");
    await page.waitForURL(/\/change-password/);

    await page.getByLabel("Текущий пароль").fill(invited.tempPassword);
    await page.getByLabel("Новый пароль").fill(newPassword);
    await page.getByLabel("Подтверждение").fill(newPassword);
    await page.getByRole("button", { name: "Сменить пароль" }).click();

    await page.waitForURL(/\/profile/);
    await expect(page.getByRole("heading", { name: "Личный кабинет" })).toBeVisible();
    await expect(page.getByText(`(${invited.login})`)).toBeVisible();
  });
});
