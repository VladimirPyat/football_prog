import { test, expect } from "@playwright/test";
import { clearAuthStorage, gotoProfile, loginAsUser } from "./fixtures/auth";

test.describe("[E2E-PROFILE-CONTACTS]", () => {
  test("user can update contacts and persist after reload", async ({ page }) => {
    await clearAuthStorage(page);
    await loginAsUser(page);
    await gotoProfile(page);

    await expect(page.getByRole("heading", { name: "Контакты" })).toBeVisible();
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByLabel("VK ID")).toBeVisible();
    await expect(page.getByLabel("Telegram ID")).toBeVisible();
    await expect(page.getByLabel("Получать уведомления")).toBeVisible();

    const vkValue = `vk_e2e_${Date.now()}`;
    await page.getByLabel("VK ID").fill(vkValue);
    await page.getByRole("button", { name: "Сохранить" }).click();
    await expect(page.getByText("Контакты сохранены")).toBeVisible();

    await page.reload();
    await expect(page.getByLabel("VK ID")).toHaveValue(vkValue);
  });
});
