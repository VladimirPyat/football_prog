import { test, expect } from "@playwright/test";
import { clearAuthStorage } from "./fixtures/auth";
import {
  ensureContestRunning,
  finalizeLoadedContestFixture,
  getRoundMatches,
  gotoAdminContest,
  reloadLoadedContestFixture,
  seedSupervisorSession,
  selectRoundByNumber,
  supervisorToken,
  waitForAdminShell,
} from "./fixtures/adminApi";
import { SUPERVISOR_PASSWORD } from "./fixtures/credentials";

test.describe("[E2E-UI-TOUR-PHASE-PANELS]", () => {
  test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD not configured");

  test.beforeAll(() => {
    reloadLoadedContestFixture();
  });

  test.beforeEach(async () => {
    await ensureContestRunning(1);
  });

  test.afterAll(() => {
    finalizeLoadedContestFixture();
  });

  test("[UI-TOUR-CLOSED] round 11 — read-only table, CTA, no LB", async ({ page }) => {
    const token = await supervisorToken();

    await clearAuthStorage(page);
    await seedSupervisorSession(page);
    await gotoAdminContest(page, 1, "/admin/rounds");
    await waitForAdminShell(page);
    const round = await selectRoundByNumber(page, token, 1, 11);

    await expect(page.getByRole("link", { name: "Перейти к результатам" })).toBeVisible();
    await expect(page.locator("tbody input")).toHaveCount(0);
    await expect(page.getByText("Таблица тура")).not.toBeVisible();
    await expect(page.getByRole("button", { name: "Опубликовать" })).not.toBeVisible();
    await expect(page.getByText("Проверить публичные результаты")).not.toBeVisible();

    const matches = await getRoundMatches(token, 1, round.id);
    const statusCell = page.locator("tbody tr").first().locator("td").nth(2);
    const firstMatch = matches[0]!;
    const kickoffPassed = Date.parse(firstMatch.date_time) <= Date.now();
    await expect(statusCell).toContainText(kickoffPassed ? "Идёт" : "Запланирован");
  });

  test("[UI-TOUR-CALCULATED] round 10 — scores, no LB, CTA only", async ({ page }) => {
    finalizeLoadedContestFixture();
    const token = await supervisorToken();

    await clearAuthStorage(page);
    await seedSupervisorSession(page);
    await gotoAdminContest(page, 1, "/admin/rounds");
    await waitForAdminShell(page);
    await selectRoundByNumber(page, token, 1, 10);

    await expect(page.getByRole("link", { name: "Перейти к результатам" })).toBeVisible();
    await expect(page.getByText("Таблица тура")).not.toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Участник" })).not.toBeVisible();
    await expect(page.locator("tbody tr").first()).toContainText(/\d+:\d+/);
    await expect(page.getByText("Проверить публичные результаты")).not.toBeVisible();
  });

  test("[UI-TOUR-PUBLISHED] round 9 — table, CTA, no Отменить on Туры", async ({ page }) => {
    const token = await supervisorToken();

    await clearAuthStorage(page);
    await seedSupervisorSession(page);
    await gotoAdminContest(page, 1, "/admin/rounds");
    await waitForAdminShell(page);
    await selectRoundByNumber(page, token, 1, 9);

    await expect(page.getByRole("link", { name: "Перейти к результатам" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Отменить" })).not.toBeVisible();
    await expect(page.getByText("Проверить публичные результаты")).not.toBeVisible();
  });
});
