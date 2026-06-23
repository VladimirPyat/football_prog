import { test, expect } from "@playwright/test";
import {
  clearAuthStorage,
  collectCorsConsoleFailures,
  fillLoginForm,
  gotoProfile,
  openLoginModal,
  submitLogin,
  waitForAuthenticatedHeader,
} from "./fixtures/auth";
import { USER_LOGIN, USER_PASSWORD } from "./fixtures/credentials";

test.describe("[E2E-LOGIN-PROFILE]", () => {
  test("visitor login redirects to profile with authenticated header", async ({ page }) => {
    const corsFailures = collectCorsConsoleFailures(page);
    await clearAuthStorage(page);

    await expect(page.getByRole("button", { name: "Вход" })).toBeVisible();

    await openLoginModal(page);
    await fillLoginForm(page, USER_LOGIN, USER_PASSWORD);
    await submitLogin(page);

    await waitForAuthenticatedHeader(page);
    await gotoProfile(page);
    await expect(page.getByText(`(${USER_LOGIN})`)).toBeVisible();

    expect(corsFailures, `[E2E-CORS-SMOKE] console errors: ${corsFailures.join("; ")}`).toEqual(
      [],
    );
  });
});
