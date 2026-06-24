import { test, expect } from "@playwright/test";
import { clearAuthStorage } from "./fixtures/auth";
import {
  addDays,
  addHours,
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

test.describe("[E2E-SUPERVISOR-24H]", () => {
  test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD not configured");

  test.beforeEach(async () => {
    await ensureContestRunning(1);
    await ensureRound10Active(1);
  });

  test("deadline 24h rule and newsletter stub on loaded round 10", async ({ page }) => {
    const token = await supervisorToken();
    const rounds = await getRounds(token, 1);
    const round10 = rounds.find((r) => r.number === 10)!;
    const matches = await getRoundMatches(token, 1, round10.id);
    const earliest = new Date(
      Math.min(...matches.map((m) => Date.parse(m.date_time))),
    );
    const invalidDeadline = addHours(earliest, -12);
    const validDeadline = addDays(earliest, -3);

    await clearAuthStorage(page);
    await seedSupervisorSession(page);
    await gotoAdminContest(page, 1, "/admin/rounds");
    await page.locator("select").first().selectOption({ label: "Тур 10 — Активен" });

    const deadlineInput = page
      .locator('div:has(> label:text-is("Дедлайн прогнозов")) input[type="datetime-local"]')
      .last();
    await deadlineInput.fill(toDatetimeLocal(invalidDeadline));
    await expect(page.getByText(/Дедлайн должен быть не позже/i)).toBeVisible();
    await expect(page.getByRole("button", { name: "Сохранить изменения" })).toBeDisabled();

    await deadlineInput.fill(toDatetimeLocal(validDeadline));
    await expect(page.getByRole("button", { name: "Сохранить изменения" })).toBeEnabled();
    await page.getByRole("button", { name: "Сохранить изменения" }).click();
    await expect(
      page.getByRole("dialog").getByText(/напоминание участникам/i),
    ).toBeVisible({ timeout: 10_000 });
    await page.getByRole("button", { name: "Закрыть" }).click();
  });
});
