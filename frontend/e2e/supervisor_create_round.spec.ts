import { test, expect } from "@playwright/test";
import { clearAuthStorage } from "./fixtures/auth";
import {
  addDays,
  addTeams,
  createDraftContest,
  createDraftRound,
  getContest,
  gotoAdminContest,
  seedSupervisorSession,
  selectRoundByNumber,
  supervisorToken,
  waitForAdminShell,
} from "./fixtures/adminApi";
import { SUPERVISOR_PASSWORD } from "./fixtures/credentials";

test.describe("[E2E-TOUR-DATE-VALIDATION]", () => {
  test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD not configured");

  test("empty match date shows human seed error", async ({ page }) => {
    const token = await supervisorToken();
    const contest = await createDraftContest(token, `E2E DateVal ${Date.now()}`, {
      total_teams: 4,
      matches_per_round: 2,
      total_rounds: 2,
    });
    const teams = await addTeams(token, contest.id, 4);

    await clearAuthStorage(page);
    await seedSupervisorSession(page);
    await gotoAdminContest(page, contest.id, "/admin/rounds");
    await waitForAdminShell(page);

    const form = page.locator("form").filter({ hasText: "Создать тур (черновик)" });
    await form.locator('input[type="datetime-local"]').first().fill("2026-11-01T10:00");
    await form.locator("select").nth(0).selectOption(String(teams[0]!.id));
    await form.locator("select").nth(1).selectOption(String(teams[1]!.id));
    await form.getByRole("button", { name: "Создать черновик тура" }).click();

    await expect(page.getByText("Укажите дату и время для каждого матча")).toBeVisible();

    await form.locator('input[type="datetime-local"]').nth(1).fill("2026-12-02T15:00");
    await form.getByRole("button", { name: "Создать черновик тура" }).click();
    await expect(page.getByText("Укажите дату и время для каждого матча")).not.toBeVisible();
  });
});

test.describe.serial("[E2E-SUPERVISOR-CREATE-ROUND] + [E2E-ADMIN-LOCK] Path A", () => {
  test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD not configured");

  let contestId: number;
  let teamIds: number[];
  let roundId: number;

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

    const now = new Date();
    const created = await createDraftRound(token, contestId, {
      number: 1,
      deadline: addDays(now, 3).toISOString(),
      matches: [
        {
          team1_id: teamIds[0]!,
          team2_id: teamIds[1]!,
          date_time: addDays(now, 7).toISOString(),
        },
      ],
    });
    roundId = created.round_id;
  });

  test.beforeEach(async ({ page }) => {
    await clearAuthStorage(page);
    await seedSupervisorSession(page);
    await gotoAdminContest(page, contestId, "/admin/rounds");
    await waitForAdminShell(page);
  });

  test("create DRAFT round via API, activate in UI, lock contest", async ({ page }) => {
    const token = await supervisorToken();
    await selectRoundByNumber(page, token, contestId, 1);

    await page.locator("section").getByRole("button", { name: "Активировать" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Активировать", exact: true }).click();

    await expect(page.getByText(/Тур активен/i).first()).toBeVisible({ timeout: 15_000 });

    const contest = await getContest(token, contestId);
    expect(contest.is_locked).toBe(true);
    expect(roundId).toBeGreaterThan(0);

    await gotoAdminContest(page, contestId, "/admin/settings/parameters");
    await expect(page.getByRole("status")).toContainText("Редактирование параметров недоступно");
  });
});
