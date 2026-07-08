import { defineConfig, devices } from "@playwright/test";
import path from "path";

const frontendDir = path.dirname(__filename);

// Project-local browser cache (gitignored). Survives agent sandbox sessions;
// default ~/.cache/ms-playwright is often empty or inaccessible in sandbox.
const projectBrowsersPath = path.join(frontendDir, ".playwright-browsers");
if (!process.env.PLAYWRIGHT_BROWSERS_PATH) {
  process.env.PLAYWRIGHT_BROWSERS_PATH = projectBrowsersPath;
}

export default defineConfig({
  testDir: "./e2e",
  globalSetup: path.join(frontendDir, "playwright.global-setup.ts"),
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["list"]],
  timeout: 30_000,
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "on-first-retry",
    ...devices["Desktop Chrome"],
  },
  webServer: {
    command: "npm run dev",
    url: "http://127.0.0.1:3000",
    reuseExistingServer: !process.env.CI,
    cwd: frontendDir,
    timeout: 120_000,
  },
});
