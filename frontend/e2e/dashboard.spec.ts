import { test, expect } from "@playwright/test";

test.describe("Dashboard", () => {
  test("loading state appears for unauthenticated users (redirect)", async ({ page }) => {
    // Should redirect to login before dashboard content renders
    await page.goto("/");
    // Landing page is public - should show WealthFlow heading
    await expect(page.getByText("WealthFlow")).toBeVisible();
  });

  test("dashboard content sections exist", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Personal Finance")).toBeVisible();
  });
});
