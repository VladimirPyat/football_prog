import { test, expect } from "@playwright/test";
import { clearAuthStorage } from "./fixtures/auth";
import {
  addDays,
  addHours,
  ensureContestRunning,
  ensureRound10Active,
  getRoundMatches,
  gotoAdminContest,
  patchRound,
  reloadLoadedContestFixture,
  seedSupervisorSession,
  selectRoundByNumber,
  supervisorToken,
  toDatetimeLocal,
  waitForAdminShell,
} from "./fixtures/adminApi";
import { SUPERVISOR_PASSWORD } from "./fixtures/credentials";

test.describe("[E2E-SUPERVISOR-24H]", () => {
  test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD not configured");

  test.beforeAll(() => {
    reloadLoadedContestFixture();
  });

  test.beforeEach(async () => {
    await ensureContestRunning(1);
    await ensureRound10Active();
  });

  test("placement allows deadline within 24h of match; lockout blocks late change", async ({
    page,
  }) => {
    const token = await supervisorToken();
    const round10 = await ensureRound10Active();
    const matches = await getRoundMatches(token, 1, round10.id);
    const earliest = new Date(Math.min(...matches.map((m) => Date.parse(m.date_time))));
    const placementDeadline = addHours(earliest, -12);
    const farDeadline = addDays(new Date(), 3);

    await patchRound(token, 1, round10.id, { deadline: farDeadline.toISOString() });

    await clearAuthStorage(page);
    await seedSupervisorSession(page);
    await gotoAdminContest(page, 1, "/admin/rounds");
    await waitForAdminShell(page);
    await selectRoundByNumber(page, token, 1, 10);

    const deadlineInput = page
      .locator('div:has(> label:text-is("Дедлайн прогнозов")) input[type="datetime-local"]')
      .last();

    await deadlineInput.fill(toDatetimeLocal(placementDeadline));
    await expect(page.getByText(/Дедлайн должен быть раньше первого матча/i)).not.toBeVisible();
    await expect(page.getByRole("button", { name: "Сохранить изменения" })).toBeEnabled();

    const nearDeadline = addHours(new Date(), 10);
    await patchRound(token, 1, round10.id, { deadline: nearDeadline.toISOString() });
    await page.reload();
    await waitForAdminShell(page);
    await selectRoundByNumber(page, token, 1, 10);

    const blockedDeadline = addHours(new Date(), 8);
    await deadlineInput.fill(toDatetimeLocal(blockedDeadline));
    await expect(page.getByText(/Изменить дедлайн можно не позже/i)).toBeVisible();
    await expect(page.getByRole("button", { name: "Сохранить изменения" })).toBeDisabled();
  });
});
