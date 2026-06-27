import { test, expect } from "@playwright/test";
import { clearAuthStorage } from "./fixtures/auth";
import {
  activateRound,
  addHours,
  addTeams,
  calculateRound,
  closeRound,
  createDraftContest,
  createDraftRound,
  ensureContestRunning,
  finalizeLoadedContestFixture,
  getRoundMatches,
  gotoAdminContest,
  reloadLoadedContestFixture,
  roundOptionLabel,
  seedSupervisorSession,
  selectRoundByLabel,
  selectRoundByNumber,
  setMatchResult,
  supervisorToken,
  waitForAdminShell,
} from "./fixtures/adminApi";
import { SUPERVISOR_PASSWORD } from "./fixtures/credentials";

test.describe("[E2E-UI-RESULTS-PREVIEW-CALC]", () => {
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

  test("CALCULATED round 10 — «Результаты участников» opens LB modal", async ({ page }) => {
    const token = await supervisorToken();

    await clearAuthStorage(page);
    await seedSupervisorSession(page);
    await gotoAdminContest(page, 1, "/admin/results");
    await waitForAdminShell(page);
    await selectRoundByLabel(page, roundOptionLabel(10, "CALCULATED"));

    await expect(page.getByText("Проверить публичные результаты")).not.toBeVisible();
    const previewBtn = page.getByRole("button", { name: "Результаты участников" });
    await expect(previewBtn).toBeVisible();
    await previewBtn.click();

    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(page.getByText(/Результаты участников — тур 10/)).toBeVisible();
    await expect(page.getByText("Таблица тура")).toBeVisible({ timeout: 15_000 });
  });

  test("CLOSED round 11 — preview control disabled with title hint", async ({ page }) => {
    const token = await supervisorToken();

    await clearAuthStorage(page);
    await seedSupervisorSession(page);
    await gotoAdminContest(page, 1, "/admin/results");
    await waitForAdminShell(page);
    await selectRoundByNumber(page, token, 1, 11);

    const disabledPreview = page.locator('[title="Сначала рассчитайте тур"]');
    await expect(disabledPreview).toBeVisible();
    await expect(disabledPreview).toContainText("Результаты участников");
  });
});

test.describe("[E2E-UI-RESULTS-PIPELINE]", () => {
  test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD not configured");

  let contestId: number;

  test.beforeAll(async () => {
    const token = await supervisorToken();
    const contest = await createDraftContest(token, `E2E Pipeline ${Date.now()}`, {
      total_teams: 4,
      matches_per_round: 2,
      total_rounds: 2,
    });
    contestId = contest.id;
    const teams = await addTeams(token, contestId, 4);
    const teamIds = teams.map((t) => t.id);
    const now = new Date();

    const created = await createDraftRound(token, contestId, {
      number: 1,
      deadline: addHours(now, -3).toISOString(),
      matches: [
        {
          team1_id: teamIds[0]!,
          team2_id: teamIds[1]!,
          date_time: addHours(now, -2).toISOString(),
        },
        {
          team1_id: teamIds[2]!,
          team2_id: teamIds[3]!,
          date_time: addHours(now, -1).toISOString(),
        },
      ],
    });
    await activateRound(token, contestId, created.round_id);
    await closeRound(token, contestId, created.round_id);

    const matches = await getRoundMatches(token, contestId, created.round_id);
    for (const m of matches) {
      await setMatchResult(token, contestId, m.id, 1, 0);
    }
  });

  test("calculate/publish buttons appear in correct phases", async ({ page }) => {
    await clearAuthStorage(page);
    await seedSupervisorSession(page);
    await gotoAdminContest(page, contestId, "/admin/results");
    await waitForAdminShell(page);
    await selectRoundByLabel(page, "Тур 1 — Дедлайн");

    await expect(page.getByRole("button", { name: "Рассчитать" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Опубликовать" })).not.toBeVisible();

    await page.getByRole("button", { name: "Рассчитать" }).click();
    await expect(page.getByRole("button", { name: "Опубликовать" })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByRole("button", { name: "Рассчитать" })).not.toBeVisible();

    await page.getByRole("button", { name: "Опубликовать" }).click();
    await expect(page.getByText("Применено")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("button", { name: "Рассчитать" })).not.toBeVisible();
    await expect(page.getByRole("button", { name: "Опубликовать" })).not.toBeVisible();
  });
});

test.describe("[E2E-UI-RESULTS-REEDIT-CLOSED]", () => {
  test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD not configured");

  let contestId: number;
  let roundId: number;

  test.beforeAll(async () => {
    const token = await supervisorToken();
    const contest = await createDraftContest(token, `E2E Reedit ${Date.now()}`, {
      total_teams: 4,
      matches_per_round: 1,
      total_rounds: 2,
    });
    contestId = contest.id;
    const teams = await addTeams(token, contestId, 4);
    const now = new Date();

    const created = await createDraftRound(token, contestId, {
      number: 1,
      deadline: addHours(now, -3).toISOString(),
      matches: [
        {
          team1_id: teams[0]!.id,
          team2_id: teams[1]!.id,
          date_time: addHours(now, -1).toISOString(),
        },
      ],
    });
    roundId = created.round_id;
    await activateRound(token, contestId, roundId);
    await closeRound(token, contestId, roundId);

    const matches = await getRoundMatches(token, contestId, roundId);
    await setMatchResult(token, contestId, matches[0]!.id, 1, 0);
  });

  test("re-edit on CLOSED; after calculate scores stay editable (B3 unlock)", async ({
    page,
  }) => {
    const token = await supervisorToken();

    await clearAuthStorage(page);
    await seedSupervisorSession(page);
    await gotoAdminContest(page, contestId, "/admin/results");
    await waitForAdminShell(page);
    await selectRoundByLabel(page, "Тур 1 — Дедлайн");

    const score1 = page.getByLabel("Счёт 1");
    await score1.fill("2");
    const saveResponse = page.waitForResponse(
      (res) => res.request().method() === "PUT" && res.url().includes("/result") && res.ok(),
    );
    await page.getByRole("button", { name: "Применить" }).click();
    await saveResponse;

    await page.getByRole("button", { name: "Рассчитать" }).click();
    await expect(page.getByText(/пересчитаются автоматически|исправить счёт/i)).toBeVisible({
      timeout: 15_000,
    });

    await expect(page.getByLabel("Счёт 1")).toBeEnabled();
    await expect(page.getByRole("button", { name: "Применить" })).toBeVisible();
  });
});

test.describe("[E2E-UI-MATCH-PHASE-RESULTS-TAB]", () => {
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

  test("round 11 CLOSED — status column uses matchPhaseLabel", async ({ page }) => {
    const token = await supervisorToken();

    await clearAuthStorage(page);
    await seedSupervisorSession(page);
    await gotoAdminContest(page, 1, "/admin/results");
    await waitForAdminShell(page);
    const round = await selectRoundByNumber(page, token, 1, 11);
    const matches = await getRoundMatches(token, 1, round.id);

    const firstMatch = matches[0]!;
    const expectedLabel =
      Date.parse(firstMatch.date_time) <= Date.now() ? "Идёт" : "Запланирован";
    await expect(page.locator("tbody tr").first().locator("td").nth(2)).toContainText(
      expectedLabel,
    );
  });
});
