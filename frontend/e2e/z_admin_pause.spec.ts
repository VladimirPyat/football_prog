import { test, expect } from "@playwright/test";
import { clearAuthStorage } from "./fixtures/auth";
import { ADMIN_PASSWORD, SUPERVISOR_PASSWORD } from "./fixtures/credentials";
import {
  adminToken,
  ensureContestRunning,
  ensureRound10Active,
  getContest,
  gotoAdminContest,
  reloadLoadedContestFixture,
  resumeContest,
  seedAdminSession,
  selectRoundByNumber,
  supervisorToken,
  waitForAdminShell,
} from "./fixtures/adminApi";

test.describe.serial("[E2E-ADMIN-PAUSE]", () => {
  test.skip(!ADMIN_PASSWORD || !SUPERVISOR_PASSWORD, "Admin/supervisor passwords not configured");

  test.beforeAll(() => {
    reloadLoadedContestFixture();
  });

  test.beforeEach(async () => {
    await ensureContestRunning(1);
    await ensureRound10Active();
  });

  test.afterEach(async () => {
    await ensureContestRunning(1);
  });

  test("pause blocks mutations and resume restores them", async ({ page }) => {
    const admin = await adminToken();
    let contest = await getContest(admin, 1);
    if (contest.status === "PAUSED") {
      await resumeContest(admin, 1);
      contest = await getContest(admin, 1);
    }
    expect(contest.status).toBe("RUNNING");

    await clearAuthStorage(page);
    await seedAdminSession(page);
    await gotoAdminContest(page, 1, "/admin/lifecycle");
    await waitForAdminShell(page);
    await page.getByRole("button", { name: "Пауза" }).click();
    await page.getByRole("button", { name: "Подтвердить" }).click();
    await expect(
      page.getByRole("status").filter({ hasText: "Конкурс на паузе" }),
    ).toBeVisible({ timeout: 10_000 });

    await gotoAdminContest(page, 1, "/admin/rounds");
    await expect(
      page.getByRole("status").filter({ hasText: "Конкурс на паузе" }),
    ).toBeVisible();
    const token = await supervisorToken();
    await selectRoundByNumber(page, token, 1, 10);
    await expect(page.getByRole("button", { name: "Сохранить изменения" })).not.toBeVisible();

    await gotoAdminContest(page, 1, "/admin/settings/parameters");
    await expect(
      page.getByRole("status").filter({ hasText: "Конкурс на паузе" }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Сохранить параметры" })).not.toBeVisible();

    await gotoAdminContest(page, 1, "/admin/results");
    await expect(page.getByRole("button", { name: "Рассчитать" })).not.toBeVisible();

    await gotoAdminContest(page, 1, "/admin/lifecycle");
    await page.getByRole("button", { name: "Возобновить" }).click();
    await page.getByRole("button", { name: "Подтвердить" }).click();
    await expect(page.locator("dd").filter({ hasText: "RUNNING" })).toBeVisible({
      timeout: 10_000,
    });

    await gotoAdminContest(page, 1, "/admin/rounds");
    await selectRoundByNumber(page, token, 1, 10);
    await expect(page.getByRole("button", { name: "Сохранить изменения" })).toBeEnabled();

    contest = await getContest(admin, 1);
    expect(contest.status).toBe("RUNNING");
  });
});
