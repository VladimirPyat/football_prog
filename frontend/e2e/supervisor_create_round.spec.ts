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

    await expect(page.getByText("ТУР АКТИВИРОВАН").first()).toBeVisible({ timeout: 15_000 });

    const contest = await getContest(token, contestId);
    expect(contest.is_locked).toBe(true);
    expect(roundId).toBeGreaterThan(0);

    await gotoAdminContest(page, contestId, "/admin/settings/parameters");
    await expect(page.getByRole("status")).toContainText("Редактирование параметров недоступно");
  });
});
