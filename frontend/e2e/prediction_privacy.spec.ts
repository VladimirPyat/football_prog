import { test, expect } from "@playwright/test";
import { loginAsDemoUser, getApiToken } from "./fixtures/auth";
import { ADMIN_LOGIN, ADMIN_PASSWORD } from "./fixtures/credentials";
import {
  ensureE2eActiveRound,
  getActiveRoundId,
  getRoundIdByNumber,
  submitPredictionsViaApi,
} from "./fixtures/predictionsApi";

test.describe("[E2E-PRED-PRIVACY-PRE]", () => {
  test("participant sees stub before deadline on predictions tab", async ({ page }) => {
    test.skip(!ADMIN_PASSWORD, "SEED_ADMIN_PASSWORD missing");
    await ensureE2eActiveRound(1);
    const roundId = await getActiveRoundId(1);
    test.skip(!roundId, "No ACTIVE round");

    const adminToken = await getApiToken(ADMIN_LOGIN, ADMIN_PASSWORD);
    const matchRes = await fetch(
      `http://127.0.0.1:8000/api/v1/contests/1/rounds/${roundId}/predictions`,
      { headers: { Authorization: `Bearer ${adminToken}` } },
    );
    const matchData = (await matchRes.json()) as { matches: { id: number }[] };
    const matchIds = matchData.matches.map((m) => m.id);
    await submitPredictionsViaApi(1, roundId!, adminToken, matchIds, 2, 1);

    await loginAsDemoUser(page);
    await page.goto("/contest/1");
    await expect(page.getByTestId("round-selector")).toBeVisible({ timeout: 15_000 });

    await expect(page.getByTestId("predictions-pre-deadline-stub")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("Будет доступно после дедлайна")).toBeVisible();
    await expect(page.getByTestId("predictions-matrix")).not.toBeVisible();
    await expect(page.getByTestId("privacy-mask")).toHaveCount(0);
  });
});

test.describe("[E2E-PRED-PRIVACY-POST]", () => {
  test("full matrix after deadline on published round", async ({ page }) => {
    const round9Id = await getRoundIdByNumber(1, 9);
    test.skip(!round9Id, "Round 9 not found");

    await loginAsDemoUser(page);
    await page.goto("/contest/1");
    await expect(page.getByTestId("round-selector")).toBeVisible({ timeout: 15_000 });

    await page.locator("#round-select").selectOption(String(round9Id));
    await expect(page.getByTestId("predictions-matrix")).toBeVisible({ timeout: 15_000 });

    const masks = page.getByTestId("privacy-mask");
    await expect(masks).toHaveCount(0);

    const userToken = await getApiToken("user", "user");
    const viewRes = await fetch(
      `http://127.0.0.1:8000/api/v1/contests/1/rounds/${round9Id}/predictions`,
      { headers: { Authorization: `Bearer ${userToken}` } },
    );
    const view = (await viewRes.json()) as { deadline_passed: boolean };
    expect(view.deadline_passed).toBe(true);
  });
});
