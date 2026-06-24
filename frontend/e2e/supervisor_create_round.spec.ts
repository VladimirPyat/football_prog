import { test, expect } from "@playwright/test";
import { clearAuthStorage } from "./fixtures/auth";
import {
  addDays,
  addHours,
  addTeams,
  createDraftContest,
  ensureContestRunning,
  ensureRound10Active,
  getContest,
  seedSupervisorSession,
  setActiveContest,
  supervisorToken,
  toDatetimeLocal,
} from "./fixtures/adminApi";
import { SUPERVISOR_PASSWORD } from "./fixtures/credentials";

test.describe.serial("[E2E-SUPERVISOR-CREATE-ROUND] + [E2E-ADMIN-LOCK] Path A", () => {
  test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD not configured");

  let contestId: number;
  let teamIds: number[];

  test.beforeAll(async () => {
    const token = await supervisorToken();
    const contest = await createDraftContest(token, `E2E Round ${Date.now()}`, {
      total_teams: 4,
      matches_per_round: 2,
      total_rounds: 2,
    });
    contestId = contest.id;
    const teams = await addTeams(token, contestId, 4);
    teamIds = teams.map((t) => t.id);
  });

  test.beforeEach(async ({ page }) => {
    await clearAuthStorage(page);
    await seedSupervisorSession(page);
    await gotoAdminContest(page, contestId, "/admin/rounds");
  });

  test("create DRAFT round, activate, lock contest", async ({ page }) => {
    await page.goto("/admin/rounds");
    const now = new Date();
    const matchDate = addDays(now, 7);
    const deadline = addDays(now, 3);

    await page
      .locator('form:has-text("Создать тур (черновик)") div:has(> label:text-is("Дедлайн прогнозов")) input')
      .fill(toDatetimeLocal(deadline));
    const teamSelects = page.locator('form:has-text("Создать тур (черновик)") select');
    await teamSelects.nth(0).selectOption(String(teamIds[0]));
    await teamSelects.nth(1).selectOption(String(teamIds[1]));
    await page
      .locator('form:has-text("Создать тур (черновик)") input[type="datetime-local"]')
      .last()
      .fill(toDatetimeLocal(matchDate));

    await page.getByRole("button", { name: "Создать черновик тура" }).click();
    await expect(page.locator("select").filter({ hasText: "Черновик" })).toBeVisible({
      timeout: 15_000,
    });

    await page.getByRole("button", { name: "Активировать" }).click();
    await page.getByRole("button", { name: "Активировать", exact: true }).click();

    await expect(page.getByText("ТУР АКТИВИРОВАН")).toBeVisible({ timeout: 15_000 });

    const token = await supervisorToken();
    const contest = await getContest(token, contestId);
    expect(contest.is_locked).toBe(true);

    await page.goto("/admin/settings/parameters");
    await expect(page.getByRole("status")).toContainText("Редактирование параметров недоступно");
  });
});
