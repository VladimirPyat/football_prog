import { test, expect } from "@playwright/test";
import { clearAuthStorage } from "./fixtures/auth";
import { ensureContestRunning, seedSupervisorSession } from "./fixtures/adminApi";
import { SUPERVISOR_PASSWORD } from "./fixtures/credentials";

test.describe("[E2E-ADMIN-LOCK] Path B — loaded contest", () => {
  test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD not configured");

  test.beforeEach(async () => {
    await ensureContestRunning(1);
  });

  test("loaded contest id=1 shows LockBanner and disabled setup controls", async ({ page }) => {
    await clearAuthStorage(page);
    await seedSupervisorSession(page);
    await page.goto("/admin/settings/parameters");
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("Редактирование параметров недоступно")).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByRole("button", { name: "Сохранить параметры" })).toBeDisabled();

    await page.goto("/admin/settings/teams");
    await expect(page.getByRole("heading", { name: "Добавить команду" })).not.toBeVisible();
    await expect(page.getByRole("button", { name: "Удалить" }).first()).not.toBeVisible();

    await page.goto("/admin/settings/participants");
    await expect(page.getByRole("button", { name: "Пригласить" })).toBeDisabled();
    await expect(page.getByRole("button", { name: "Удалить" }).first()).not.toBeVisible();
  });
});
