import { test, expect } from "@playwright/test";

test.describe("Notifications", () => {
  test("no notification bell on public landing page", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByLabel(/notifications/i)).not.toBeVisible();
  });

  test("no notification bell on login page", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByLabel(/notifications/i)).not.toBeVisible();
  });

  test("no notification bell on register page", async ({ page }) => {
    await page.goto("/register");
    await expect(page.getByLabel(/notifications/i)).not.toBeVisible();
  });
});
