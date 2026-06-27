import { test, expect } from "@playwright/test";
import { clearAuthStorage } from "./fixtures/auth";
import {
  addDays,
  ensureContestRunning,
  ensureRound10Active,
  getRoundMatches,
  gotoAdminContest,
  reloadLoadedContestFixture,
  seedSupervisorSession,
  selectRoundByNumber,
  supervisorToken,
  toDatetimeLocal,
  waitForAdminShell,
} from "./fixtures/adminApi";
import { SUPERVISOR_PASSWORD } from "./fixtures/credentials";

test.describe("[E2E-SUPERVISOR-ACTIVE-ROUND]", () => {
  test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD not configured");

  test.beforeAll(() => {
    reloadLoadedContestFixture();
  });

  test.beforeEach(async () => {
    await ensureContestRunning(1);
    await ensureRound10Active();
  });

  test("ACTIVE round: no team structure edit; reschedule and postpone actions", async ({
    page,
  }) => {
    const token = await supervisorToken();
    const round10 = await ensureRound10Active();

    await clearAuthStorage(page);
    await seedSupervisorSession(page);
    await gotoAdminContest(page, 1, "/admin/rounds");
    await waitForAdminShell(page);
    await selectRoundByNumber(page, token, 1, 10);

    await expect(page.getByText(/Состав матчей изменить нельзя/i).first()).toBeVisible();
    await expect(page.locator("tbody select")).toHaveCount(1);

    const newDate = addDays(new Date(), 2);
    const dateInput = page.locator('tbody input[type="datetime-local"]').first();
    await dateInput.fill(toDatetimeLocal(newDate));
    await dateInput.dispatchEvent("change");
    const saveBtn = page.getByRole("button", { name: "Сохранить изменения" });
    await expect(saveBtn).toBeEnabled();
    const saveResponse = page.waitForResponse(
      (res) =>
        res.request().method() === "PATCH" &&
        res.url().includes("/admin/rounds/") &&
        res.ok(),
    );
    await page.getByRole("button", { name: "Сохранить изменения" }).click();
    await saveResponse;

    const statusSelect = page.locator("tbody select").first();
    await statusSelect.selectOption({ value: "POSTPONED" });
    await page.getByRole("button", { name: "Подтвердить" }).click();
    await page.waitForResponse(
      (res) =>
        res.request().method() === "PATCH" &&
        res.url().includes("/admin/rounds/") &&
        res.ok(),
    );

    const matches = await getRoundMatches(token, 1, round10.id);
    expect(matches[0]?.status).toBe("POSTPONED");
  });
});
