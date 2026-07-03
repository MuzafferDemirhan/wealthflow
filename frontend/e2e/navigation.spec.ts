import { test, expect } from "@playwright/test";

test.describe("Authenticated Navigation", () => {
  test("redirects to login when accessing protected route", async ({ page }) => {
    await page.goto("/accounts");
    await expect(page).toHaveURL(/\/login/);
  });

  test("redirects to login when accessing portfolio", async ({ page }) => {
    await page.goto("/portfolio");
    await expect(page).toHaveURL(/\/login/);
  });

  test("redirects to login when accessing budgets", async ({ page }) => {
    await page.goto("/budgets");
    await expect(page).toHaveURL(/\/login/);
  });

  test("redirects to login when accessing transactions", async ({ page }) => {
    await page.goto("/transactions");
    await expect(page).toHaveURL(/\/login/);
  });

  test("redirects to login when accessing reports", async ({ page }) => {
    await page.goto("/reports/net-worth");
    await expect(page).toHaveURL(/\/login/);
  });

  test("redirects to login when accessing connect", async ({ page }) => {
    await page.goto("/connect");
    await expect(page).toHaveURL(/\/login/);
  });

  test("redirects to login when accessing profile", async ({ page }) => {
    await page.goto("/profile");
    await expect(page).toHaveURL(/\/login/);
  });
});
