import { test, expect } from "@playwright/test";
import { clearAuthStorage } from "./fixtures/auth";
import {
  createDraftContest,
  fulfillStartPrerequisites,
  gotoAdminContest,
  seedSupervisorSession,
  startContest,
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

test.describe("[E2E-CREATE-MODAL]", () => {
  test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD not configured");

  test.beforeEach(async ({ page }) => {
    await clearAuthStorage(page);
    await seedSupervisorSession(page);
    await page.goto("/admin/settings/parameters");
    await waitForAdminShell(page);
  });

  test("create modal has only name and slug fields", async ({ page }) => {
    await page.getByRole("button", { name: "+ Новый конкурс" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByRole("heading", { name: "Новый конкурс" })).toBeVisible();
    await expect(dialog.getByLabel("Название")).toBeVisible();
    await expect(dialog.getByLabel("Короткое имя (slug)")).toBeVisible();
    await expect(dialog.getByText("Короткое имя для ссылки")).toBeVisible();
    await expect(dialog.getByText("Команд")).not.toBeVisible();
    await expect(dialog.getByText("Круговая система")).not.toBeVisible();
  });
});

test.describe("[E2E-PARAMS-ROUND-ROBIN]", () => {
  test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD not configured");

  let contestId: number;

  test.beforeEach(async ({ page }) => {
    const token = await supervisorToken();
    const contest = await createDraftContest(token, `E2E RR ${Date.now()}`, {
      total_teams: 8,
      matches_per_round: 4,
      total_rounds: 14,
      is_round_robin: true,
    });
    contestId = contest.id;

    await clearAuthStorage(page);
    await seedSupervisorSession(page);
    await gotoAdminContest(page, contestId, "/admin/settings/parameters");
    await waitForAdminShell(page);
  });

  test("round-robin auto-fills matches and rounds when teams change", async ({ page }) => {
    const teamsInput = page.locator('div:has(> label:text-is("Команд")) input');
    const matchesInput = page.locator('div:has(> label:text-is("Матчей в туре")) input');
    const roundsInput = page.locator('div:has(> label:text-is("Туров")) input');

    await expect(matchesInput).toHaveValue("4");
    await expect(roundsInput).toHaveValue("14");
    await expect(matchesInput).toBeDisabled();
    await expect(roundsInput).toBeDisabled();

    await teamsInput.fill("10");
    await expect(matchesInput).toHaveValue("5");
    await expect(roundsInput).toHaveValue("18");
  });

  test("arbitrary mode allows editing matches and rounds", async ({ page }) => {
    await page.getByLabel("Произвольное количество").check();
    const matchesInput = page.locator('div:has(> label:text-is("Матчей в туре")) input');
    const roundsInput = page.locator('div:has(> label:text-is("Туров")) input');
    await expect(matchesInput).toBeEnabled();
    await expect(roundsInput).toBeEnabled();
    await matchesInput.fill("3");
    await roundsInput.fill("5");
    await page.getByRole("button", { name: "Сохранить параметры" }).click();
    await expect(page.getByText("Параметры сохранены")).toBeVisible({ timeout: 10_000 });
  });
});

test.describe("[E2E-ADMIN-START]", () => {
  test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD not configured");

  let contestId: number;

  test.beforeEach(async ({ page }) => {
    const token = await supervisorToken();
    const contest = await createDraftContest(token, `E2E Start ${Date.now()}`, {
      total_teams: 4,
      matches_per_round: 2,
      total_rounds: 6,
    });
    contestId = contest.id;
    await fulfillStartPrerequisites(token, contestId);

    await clearAuthStorage(page);
    await seedSupervisorSession(page);
    await gotoAdminContest(page, contestId, "/admin/settings/parameters");
    await waitForAdminShell(page);
  });

  test("start contest via UI locks parameters", async ({ page }) => {
    await expect(page.getByText("Конкурс готов к запуску")).toBeVisible();
    await expect(page.getByRole("button", { name: "Запустить конкурс" })).toBeEnabled();
    await page.getByRole("button", { name: "Запустить конкурс" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Запустить", exact: true }).click();
    await expect(page.getByText("Конкурс запущен")).toBeVisible({ timeout: 15_000 });
    await expect(
      page.getByRole("status").filter({ hasText: "Редактирование параметров недоступно" }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Сохранить параметры" })).not.toBeVisible();
  });

  test("start contest via API locks parameters", async ({ page }) => {
    const token = await supervisorToken();
    const updated = await startContest(token, contestId);
    expect(updated.is_locked).toBe(true);
    expect(updated.status).toBe("RUNNING");

    await page.reload();
    await waitForAdminShell(page);
    await expect(
      page.getByRole("status").filter({ hasText: "Редактирование параметров недоступно" }),
    ).toBeVisible();
  });

  test("start blocked on fresh draft without setup", async ({ page }) => {
    const token = await supervisorToken();
    const fresh = await createDraftContest(token, `E2E Start Blocked ${Date.now()}`, {
      total_teams: 4,
      matches_per_round: 2,
      total_rounds: 6,
    });
    await gotoAdminContest(page, fresh.id, "/admin/settings/parameters");
    await waitForAdminShell(page);
    await expect(page.getByText("Перед запуском выполните настройку")).toBeVisible();
    await expect(page.getByRole("button", { name: "Запустить конкурс" })).toBeDisabled();
  });
});
