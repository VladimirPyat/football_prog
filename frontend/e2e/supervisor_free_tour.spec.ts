import { test, expect } from "@playwright/test";
import { clearAuthStorage } from "./fixtures/auth";
import {
  addDays,
  ensureContestRunning,
  ensureRound10Active,
  getRoundMatches,
  gotoAdminContest,
  reloadLoadedContestFixture,
  seedSupervisorSession,
  selectRoundByNumber,
  patchRound,
  supervisorToken,
  toDatetimeLocal,
  waitForAdminShell,
} from "./fixtures/adminApi";
import { SUPERVISOR_PASSWORD } from "./fixtures/credentials";

test.describe("[E2E-SUPERVISOR-FREE-TOUR]", () => {
  test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD not configured");

  test.beforeAll(() => {
    reloadLoadedContestFixture();
  });

  test.beforeEach(async () => {
    await ensureContestRunning(1);
    await ensureRound10Active();
  });

  test("free tour lists only POSTPONED matches", async ({ page }) => {
    const token = await supervisorToken();
    const contestId = 1;
    const round10 = await ensureRound10Active();
    const beforeMatches = await getRoundMatches(token, contestId, round10.id);
    const scheduled = beforeMatches.find((m) => m.status === "SCHEDULED");
    const target = beforeMatches.find((m) => m.status === "SCHEDULED") ?? beforeMatches[0];
    expect(target).toBeTruthy();

    await patchRound(token, contestId, round10.id, {
      matches: [{ match_id: target!.id, status: "POSTPONED" }],
    });

    await clearAuthStorage(page);
    await seedSupervisorSession(page);
    await gotoAdminContest(page, contestId, "/admin/rounds");
    await waitForAdminShell(page);
    await selectRoundByNumber(page, token, contestId, 10);
    await page.getByRole("button", { name: "+ Добавить свободный тур" }).click();

    const modal = page.locator(".fixed.inset-0");
    if (scheduled && scheduled.id !== target!.id) {
      await expect(modal.getByText(scheduled.team1)).not.toBeVisible();
    }
    const postponedLabel = modal.locator("label").filter({ hasText: target!.team1 });
    await expect(postponedLabel).toBeVisible();
    await postponedLabel.locator('input[type="checkbox"]').check();
    const newDate = addDays(new Date(), 14);
    await postponedLabel.locator('input[type="datetime-local"]').fill(toDatetimeLocal(newDate));
    await modal.locator('div:has(> label:text-is("Дедлайн тура")) input').fill(
      toDatetimeLocal(addDays(newDate, -2)),
    );
    await modal.getByRole("button", { name: "Создать свободный тур" }).click();

    await expect(page.getByText(/свободн|тур/i).first()).toBeVisible({ timeout: 15_000 });
    const afterMatches = await getRoundMatches(token, contestId, round10.id);
    expect(afterMatches.some((m) => m.id === target!.id)).toBe(false);
  });
});
