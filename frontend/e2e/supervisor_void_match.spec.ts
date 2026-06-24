import { test, expect } from "@playwright/test";
import { clearAuthStorage } from "./fixtures/auth";
import {
  ensureContestRunning,
  getLeaderboard,
  getRounds,
  seedSupervisorSession,
  setActiveContest,
  supervisorToken,
} from "./fixtures/adminApi";
import { SUPERVISOR_PASSWORD } from "./fixtures/credentials";

test.describe("[E2E-SUPERVISOR-VOID]", () => {
  test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD not configured");

  test.beforeEach(async () => {
    await ensureContestRunning(1);
    const token = await supervisorToken();
    const rounds = await getRounds(token, 1);
    const round9 = rounds.find((r) => r.number === 9);
    if (round9?.status === "CLOSED") {
      await fetch(`http://127.0.0.1:8000/api/v1/contests/1/admin/rounds/9/calculate`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: "{}",
      });
    }
    if (round9?.status === "CALCULATED") {
      await fetch(`http://127.0.0.1:8000/api/v1/contests/1/admin/rounds/9/publish`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: "{}",
      });
    }
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
    await page.locator("select").first().selectOption({ label: "Тур 9 — Опубликован" });

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
