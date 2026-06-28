import { expect, type Page } from "@playwright/test";

/** Wait for predict form and enter edit mode if a prior save exists. */
export async function ensurePredictionEditing(page: Page): Promise<void> {
  await expect(page.locator('input[inputmode="numeric"]').first()).toBeVisible({
    timeout: 15_000,
  });
  const editBtn = page.getByRole("button", { name: "Редактировать" });
  if (await editBtn.isVisible()) {
    await editBtn.click();
  }
}

/** Clear all score inputs on the predict form. */
export async function clearAllScores(page: Page): Promise<void> {
  await ensurePredictionEditing(page);
  const inputs = page.locator('input[inputmode="numeric"]');
  const count = await inputs.count();
  for (let i = 0; i < count; i++) {
    await inputs.nth(i).fill("");
  }
}

/** Fill score inputs on predict form — one pair per match row in order. */
export async function fillMatchScores(
  page: Page,
  scores: { score1: number; score2: number }[],
): Promise<void> {
  await ensurePredictionEditing(page);
  const inputs = page.locator('input[inputmode="numeric"]');
  const count = await inputs.count();
  expect(count).toBeGreaterThanOrEqual(scores.length * 2);

  for (let i = 0; i < scores.length; i++) {
    await inputs.nth(i * 2).fill(String(scores[i].score1));
    await inputs.nth(i * 2 + 1).fill(String(scores[i].score2));
  }
}

export async function fillAllMatchesDefault(page: Page, count = 8): Promise<void> {
  const scores = Array.from({ length: count }, (_, i) => ({
    score1: (i % 3) + 1,
    score2: i % 2,
  }));
  await fillMatchScores(page, scores);
}
