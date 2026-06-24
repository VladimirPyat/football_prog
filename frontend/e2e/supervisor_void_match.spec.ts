import { test, expect } from "@playwright/test";
import { clearAuthStorage } from "./fixtures/auth";
import {
  ensureContestRunning,
  ensureRoundPublished,
  getLeaderboard,
  gotoAdminContest,
  reloadLoadedContestFixture,
  seedSupervisorSession,
  selectRoundByNumber,
  supervisorToken,
  waitForAdminShell,
} from "./fixtures/adminApi";
import { SUPERVISOR_PASSWORD } from "./fixtures/credentials";

test.describe("[E2E-SUPERVISOR-VOID]", () => {
  test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD not configured");

  test.beforeAll(() => {
    reloadLoadedContestFixture();
  });

  test.beforeEach(async () => {
    await ensureContestRunning(1);
    const token = await supervisorToken();
    await ensureRoundPublished(token, 1, 9);
  });

  test("VOID match updates leaderboard on published round 9", async ({ page }) => {
    const token = await supervisorToken();
    const before = await getLeaderboard(token, 1);
    expect(before.length).toBeGreaterThan(0);
    const sampleUser = before[0]!;
    const pointsBefore = sampleUser.total_with_bonus3;

    await clearAuthStorage(page);
    await seedSupervisorSession(page);
    await gotoAdminContest(page, 1, "/admin/results");
    await waitForAdminShell(page);
    await selectRoundByNumber(page, token, 1, 9);

    const voidBtn = page.getByRole("button", { name: "Отменить" }).first();
    await expect(voidBtn).toBeVisible({ timeout: 10_000 });
    await voidBtn.click();
    await page.getByRole("button", { name: "Отменить матч" }).click();

    const after = await getLeaderboard(token, 1);
    const sampleAfter = after.find((r) => r.user_id === sampleUser.user_id);
    expect(sampleAfter).toBeTruthy();
    expect(sampleAfter!.total_with_bonus3).toBeLessThanOrEqual(pointsBefore);
  });
});
