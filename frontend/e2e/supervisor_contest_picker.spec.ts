import { test, expect } from "@playwright/test";
import { clearAuthStorage, loginAsSupervisor } from "./fixtures/auth";
import { ACTIVE_CONTEST_KEY, SUPERVISOR_PASSWORD } from "./fixtures/credentials";

test.describe("[E2E-SUPERVISOR-PICKER]", () => {
  test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD not configured");

  test("supervisor sees contest switcher with contests", async ({ page }) => {
    await clearAuthStorage(page);
    await loginAsSupervisor(page);

    const picker = page.getByLabel("Выбор конкурса");
    await expect(picker).toBeVisible();
    const options = picker.locator("option");
    await expect(options).not.toHaveCount(0);

    const firstValue = await options.first().getAttribute("value");
    expect(firstValue).toBeTruthy();

    await picker.selectOption({ index: 0 });
    await page.waitForURL(/\/contest\/\d+/);

    const storedContestId = await page.evaluate(
      (key) => localStorage.getItem(key),
      ACTIVE_CONTEST_KEY,
    );
    expect(storedContestId).toBe(firstValue);
  });
});
