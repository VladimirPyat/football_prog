import { test, expect } from "@playwright/test";
import { clearAuthStorage } from "./fixtures/auth";
import {
  addDays,
  ensureContestRunning,
  ensureRound10Active,
  getRoundMatches,
  getRounds,
  gotoAdminContest,
  seedSupervisorSession,
  supervisorToken,
  toDatetimeLocal,
} from "./fixtures/adminApi";
import { SUPERVISOR_PASSWORD } from "./fixtures/credentials";

test.describe("[E2E-SUPERVISOR-ACTIVE-ROUND]", () => {
  test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD not configured");

  test.beforeEach(async () => {
    await ensureContestRunning(1);
    await ensureRound10Active(1);
  });

  test("ACTIVE round 10: structure frozen, status and date editable", async ({ page }) => {
    const token = await supervisorToken();
    const rounds = await getRounds(token, 1);
    const round10 = rounds.find((r) => r.number === 10)!;

    await clearAuthStorage(page);
    await seedSupervisorSession(page);
    await gotoAdminContest(page, 1, "/admin/rounds");
    await page.locator("select").first().selectOption({ label: "Тур 10 — Активен" });

    await expect(page.getByText("ТУР АКТИВИРОВАН")).toBeVisible();
    await expect(page.getByRole("button", { name: "+ Добавить матч" })).not.toBeVisible();

    const statusSelect = page.locator("tbody select").first();
    await statusSelect.selectOption("POSTPONED");
    const newDate = addDays(new Date(), 30);
    await page.locator('tbody input[type="datetime-local"]').first().fill(toDatetimeLocal(newDate));
    await page.getByRole("button", { name: "Сохранить изменения" }).click();

    const matches = await getRoundMatches(token, 1, round10.id);
    expect(matches[0]?.status).toBe("POSTPONED");
  });
});
