import { test, expect } from "@playwright/test";
import { loginAsDemoUser, getApiToken } from "./fixtures/auth";
import { SUPERVISOR_LOGIN, SUPERVISOR_PASSWORD } from "./fixtures/credentials";
import {
  ensureE2eActiveRound,
  getActiveRoundId,
  patchRoundDeadlineFuture,
} from "./fixtures/predictionsApi";

test.describe("[E2E-PRED-DEADLINE-WARN]", () => {
  test("shows warning banner when deadline within 24h", async ({ page }) => {
    await ensureE2eActiveRound(1);
    const roundId = await getActiveRoundId(1);
    test.skip(!roundId, "No ACTIVE round");
    test.skip(!SUPERVISOR_PASSWORD, "SEED_SUPERVISOR_PASSWORD missing");

    const supervisorToken = await getApiToken(SUPERVISOR_LOGIN, SUPERVISOR_PASSWORD);
    await patchRoundDeadlineFuture(1, roundId!, supervisorToken, 12);

    await loginAsDemoUser(page);
    await page.goto(`/contest/1/predict/${roundId}`);

    await expect(page.getByTestId("deadline-warning-banner")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId("deadline-warning-banner")).toContainText(/24 час/);
    await ensureE2eActiveRound(1);
  });
});
