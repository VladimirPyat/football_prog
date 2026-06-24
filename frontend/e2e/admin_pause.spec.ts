import { test, expect } from "@playwright/test";
import { clearAuthStorage } from "./fixtures/auth";
import {
  ADMIN_PASSWORD,
  SUPERVISOR_PASSWORD,
} from "./fixtures/credentials";
import {
  ensureContestRunning,
  getContest,
  resumeContest,
  seedAdminSession,
  setActiveContest,
  supervisorToken,
} from "./fixtures/adminApi";

test.describe("[E2E-ADMIN-PAUSE]", () => {
  test.skip(!ADMIN_PASSWORD || !SUPERVISOR_PASSWORD, "Admin/supervisor passwords not configured");

  test.afterEach(async () => {
    await ensureContestRunning(1);
  });

  test("pause blocks mutations and resume restores them", async ({ page }) => {
    await ensureContestRunning(1);
    const token = await supervisorToken();
    let contest = await getContest(token, 1);
    if (contest.status === "PAUSED") {
      await resumeContest(token, 1);
      contest = await getContest(token, 1);
    }

    await clearAuthStorage(page);
    await seedAdminSession(page);
    await setActiveContest(page, 1);
    await page.goto("/admin/lifecycle");
    await page.waitForLoadState("networkidle");
    await page.getByRole("button", { name: "Пауза" }).click();
    await page.getByRole("button", { name: "Подтвердить" }).click();
    await expect(page.getByText("Конкурс на паузе")).toBeVisible({ timeout: 10_000 });

    await page.goto("/admin/rounds");
    await expect(page.getByText("Конкурс на паузе")).toBeVisible();
    await page.locator("select").first().selectOption({ label: /Тур 10/ });
    await expect(page.getByRole("button", { name: "Сохранить изменения" })).toBeDisabled();

    await page.goto("/admin/settings/parameters");
    await expect(page.getByText("Конкурс на паузе")).toBeVisible();
    await expect(page.getByRole("button", { name: "Сохранить параметры" })).toBeDisabled();

    await page.goto("/admin/results");
    await expect(page.getByRole("button", { name: "Рассчитать" })).not.toBeVisible();

    await page.goto("/admin/lifecycle");
    await page.getByRole("button", { name: "Возобновить" }).click();
    await page.getByRole("button", { name: "Подтвердить" }).click();
    await expect(page.locator("dd").filter({ hasText: "RUNNING" })).toBeVisible({
      timeout: 10_000,
    });

    await page.goto("/admin/rounds");
    await page.locator("select").first().selectOption({ label: /Тур 10/ });
    await expect(page.getByRole("button", { name: "Сохранить изменения" })).toBeEnabled();

    contest = await getContest(await supervisorToken(), 1);
    expect(contest.status).toBe("RUNNING");
  });
});
