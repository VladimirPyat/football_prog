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

  test("ACTIVE round 10: structure frozen, status and date editable", async ({ page }) => {
    const token = await supervisorToken();
    const round10 = await ensureRound10Active();

    await clearAuthStorage(page);
    await seedSupervisorSession(page);
    await gotoAdminContest(page, 1, "/admin/rounds");
    await waitForAdminShell(page);
    await selectRoundByNumber(page, token, 1, 10);

    await expect(page.getByText("ТУР АКТИВИРОВАН")).toBeVisible();
    await expect(page.getByRole("button", { name: "+ Добавить матч" })).not.toBeVisible();

    const statusSelect = page.locator("tbody select").first();
    await statusSelect.selectOption({ value: "POSTPONED" });
    const newDate = addDays(new Date(), 30);
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
    await saveBtn.click();
    await saveResponse;

    const matches = await getRoundMatches(token, 1, round10.id);
    expect(matches[0]?.status).toBe("POSTPONED");
  });
});
