import { test, expect } from "@playwright/test";
import { clearAuthStorage } from "./fixtures/auth";
import {
  ensureContestRunning,
  getPublicResults,
  getRounds,
  seedSupervisorSession,
  setActiveContest,
  supervisorToken,
} from "./fixtures/adminApi";
import { SUPERVISOR_PASSWORD } from "./fixtures/credentials";

test.describe("[E2E-SUPERVISOR-RESULTS]", () => {
  test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD not configured");

  test.beforeEach(async () => {
    await ensureContestRunning(1);
    const token = await supervisorToken();
    const rounds = await getRounds(token, 1);
    const round9 = rounds.find((r) => r.number === 9);
    if (round9?.status === "CLOSED") {
      await fetch(`http://127.0.0.1:8000/api/v1/contests/1/admin/rounds/9/calculate`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: "{}",
      });
    }
  });

  test("publish calculated round 9 on loaded contest", async ({ page }) => {
    await clearAuthStorage(page);
    await seedSupervisorSession(page);
    await gotoAdminContest(page, 1, "/admin/results");
    await page.locator("select").first().selectOption({ label: "Тур 9 — Рассчитан" });

    await page.getByRole("button", { name: "Опубликовать" }).click();
    await expect(page.getByText("Применено")).toBeVisible({ timeout: 15_000 });

    const token = await supervisorToken();
    const rounds = await getRounds(token, 1);
    expect(rounds.find((r) => r.number === 9)?.status).toBe("PUBLISHED");

    const results = await getPublicResults(token, 1, 9);
    expect(results).toBeTruthy();
  });
});
