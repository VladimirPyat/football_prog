import { test, expect } from "@playwright/test";
import path from "path";
import { clearAuthStorage } from "./fixtures/auth";
import {
  addTeam,
  createDraftContest,
  getContest,
  gotoAdminContest,
  seedSupervisorSession,
  supervisorToken,
  waitForAdminShell,
} from "./fixtures/adminApi";
import { SUPERVISOR_PASSWORD } from "./fixtures/credentials";

test.describe("[E2E-ADMIN-LOGO]", () => {
  test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD not configured");

  test("[SKIP-LOGO-FIXTURE] upload logo on DRAFT contest", async ({ page }) => {
    const token = await supervisorToken();
    const contest = await createDraftContest(token, `E2E Logo ${Date.now()}`);
    await addTeam(token, contest.id, `Logo Team ${Date.now()}`, "LGOT");

    await clearAuthStorage(page);
    await seedSupervisorSession(page);
    await gotoAdminContest(page, contest.id, "/admin/settings/teams");
    await waitForAdminShell(page);

    const logoPath = path.resolve(__dirname, "../public/assets/default-team-logo.jpg");
    const uploadBtn = page.getByRole("button", { name: "Загрузить логотип" }).first();
    const fileChooserPromise = page.waitForEvent("filechooser");
    await uploadBtn.click();
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(logoPath);
    await expect(page.getByText("Логотип загружен")).toBeVisible({ timeout: 15_000 });

    const updated = await getContest(token, contest.id);
    expect(updated.is_locked).toBe(false);
    await expect(uploadBtn).toBeEnabled();
  });
});
