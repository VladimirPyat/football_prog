import { test, expect } from "@playwright/test";
import { clearAuthStorage } from "./fixtures/auth";
import {
  activateRound,
  addHours,
  addTeams,
  closeRound,
  createDraftContest,
  createDraftRound,
  gotoAdminContest,
  seedSupervisorSession,
  selectRoundByLabel,
  supervisorToken,
  waitForAdminShell,
} from "./fixtures/adminApi";
import { SUPERVISOR_PASSWORD } from "./fixtures/credentials";

test.describe("[E2E-UI-RESULTS-KICKOFF-GATE]", () => {
  test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD not configured");

  let contestId: number;
  let teamIds: number[];

  test.beforeAll(async () => {
    const token = await supervisorToken();
    const contest = await createDraftContest(token, `E2E Kickoff ${Date.now()}`, {
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
      deadline: addHours(now, -3).toISOString(),
      matches: [
        {
          team1_id: teamIds[0]!,
          team2_id: teamIds[1]!,
          date_time: addHours(now, -1).toISOString(),
        },
        {
          team1_id: teamIds[2]!,
          team2_id: teamIds[3]!,
          date_time: addHours(now, 2).toISOString(),
        },
      ],
    });
    await activateRound(token, contestId, created.round_id);
    await closeRound(token, contestId, created.round_id);
  });

  test("pre-kickoff row disabled; post-kickoff editable on CLOSED", async ({ page }) => {
    await clearAuthStorage(page);
    await seedSupervisorSession(page);
    await gotoAdminContest(page, contestId, "/admin/results");
    await waitForAdminShell(page);
    await selectRoundByLabel(page, "Тур 1 — Дедлайн");

    await expect(
      page.getByText("Счёт можно вносить после времени начала каждого матча"),
    ).toBeVisible();

    const rows = page.locator("tbody tr");
    const pastRow = rows.nth(0);
    const futureRow = rows.nth(1);

    await expect(pastRow.getByLabel("Счёт 1")).toBeEnabled();
    await expect(pastRow.getByRole("button", { name: "Применить" })).toBeVisible();

    await expect(futureRow.getByLabel("Счёт 1")).toBeDisabled();
    await expect(futureRow.getByText("Матч ещё не начался")).toBeVisible();
  });
});
