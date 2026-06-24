import { test, expect } from "@playwright/test";
import { clearAuthStorage } from "./fixtures/auth";
import {
  createDraftContest,
  gotoAdminContest,
  seedSupervisorSession,
  supervisorToken,
  waitForAdminShell,
} from "./fixtures/adminApi";
import { SUPERVISOR_PASSWORD } from "./fixtures/credentials";

test.describe("[E2E-ADMIN-SETUP]", () => {
  test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD not configured");

  let contestId: number;
  let contestName: string;

  test.beforeEach(async ({ page }) => {
    const token = await supervisorToken();
    contestName = `E2E Setup ${Date.now()}`;
    const contest = await createDraftContest(token, contestName, {
      total_teams: 4,
      matches_per_round: 2,
      total_rounds: 2,
    });
    contestId = contest.id;

    await clearAuthStorage(page);
    await seedSupervisorSession(page);
    await gotoAdminContest(page, contestId, "/admin/settings/parameters");
    await waitForAdminShell(page);
  });

  test("parameters save persists after reload", async ({ page }) => {
    await expect(page.getByText("Редактирование параметров недоступно")).not.toBeVisible();
    const teamsInput = page.locator('div:has(> label:text-is("Команд")) input');
    await teamsInput.fill("6");
    await page.getByRole("button", { name: "Сохранить параметры" }).click();
    await expect(page.getByText("Параметры сохранены")).toBeVisible({ timeout: 10_000 });
    await page.reload();
    await expect(teamsInput).toHaveValue("6");
  });

  test("teams CRUD enabled in SETUP", async ({ page }) => {
    await page.goto("/admin/settings/teams");
    const addSection = page.locator("section").filter({ hasText: "Добавить команду" });
    await addSection.locator('div:has(> label:text-is("Название")) input').fill("Alpha FC");
    await addSection.locator('div:has(> label:text-matches("Сокращение")) input').fill("ALP");
    await page.getByRole("button", { name: "Добавить" }).click();
    await expect(page.getByText("Alpha FC")).toBeVisible();
    await addSection.locator('div:has(> label:text-is("Название")) input').fill("Beta FC");
    await addSection.locator('div:has(> label:text-matches("Сокращение")) input').fill("BET");
    await page.getByRole("button", { name: "Добавить" }).click();
    await expect(page.getByText("Beta FC")).toBeVisible();
    await expect(page.getByRole("button", { name: "Добавить" })).toBeEnabled();
  });

  test("participant invite shows credentials modal", async ({ page }) => {
    await gotoAdminContest(page, contestId, "/admin/settings/participants");
    await waitForAdminShell(page);
    await expect(page.getByRole("heading", { name: "Пригласить участника" })).toBeVisible({
      timeout: 15_000,
    });
    const inviteForm = page
      .locator("form")
      .filter({ has: page.getByRole("heading", { name: "Пригласить участника" }) });
    await inviteForm.locator('div:has(> label:text-is("Email")) input').fill(
      `e2e_invite_${Date.now()}@example.com`,
    );
    await inviteForm.locator('div:has(> label:text-is("Имя")) input').fill("Test");
    await inviteForm.locator('div:has(> label:text-is("Фамилия")) input').fill("User");
    await page.getByRole("button", { name: "Пригласить" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(page.getByRole("dialog").getByText("Логин", { exact: true })).toBeVisible();
    await expect(page.getByText("Временный пароль")).toBeVisible();
    await expect(page.getByRole("button", { name: "Удалить" }).first()).toBeEnabled();
  });
});
