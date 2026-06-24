import { test, expect } from "@playwright/test";
import { clearAuthStorage } from "./fixtures/auth";
import {
  calculateRound,
  ensureContestRunning,
  getPublicResults,
  getRounds,
  gotoAdminContest,
  reloadLoadedContestFixture,
  roundOptionLabel,
  seedSupervisorSession,
  selectRoundByLabel,
  supervisorToken,
  waitForAdminShell,
} from "./fixtures/adminApi";
import { SUPERVISOR_PASSWORD } from "./fixtures/credentials";

test.describe("[E2E-SUPERVISOR-RESULTS]", () => {
  test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD not configured");

  test.beforeAll(() => {
    reloadLoadedContestFixture();
  });

  test.beforeEach(async () => {
    await ensureContestRunning(1);
    const token = await supervisorToken();
    const rounds = await getRounds(token, 1);
    const round9 = rounds.find((r) => r.number === 9);
    if (round9?.status === "CLOSED") {
      await calculateRound(token, 1, round9.id);
    }
  });

  test("publish calculated round 9 on loaded contest", async ({ page }) => {
    const token = await supervisorToken();
    let rounds = await getRounds(token, 1);
    const round9 = rounds.find((r) => r.number === 9)!;

    await clearAuthStorage(page);
    await seedSupervisorSession(page);
    await gotoAdminContest(page, 1, "/admin/results");
    await waitForAdminShell(page);
    await selectRoundByLabel(page, roundOptionLabel(9, "CALCULATED"));

    await page.getByRole("button", { name: "Опубликовать" }).click();
    await expect(page.getByText("Применено")).toBeVisible({ timeout: 15_000 });

    rounds = await getRounds(token, 1);
    expect(rounds.find((r) => r.number === 9)?.status).toBe("PUBLISHED");

    const results = await getPublicResults(token, 1, round9.id);
    expect(results).toBeTruthy();
  });
});
