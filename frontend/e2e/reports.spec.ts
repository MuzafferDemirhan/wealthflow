import { test, expect } from "@playwright/test";

test.describe("Reports", () => {
  test("all report pages redirect to login for unauthenticated users", async ({ page }) => {
    await page.goto("/reports/category-breakdown");
    await expect(page).toHaveURL(/\/login/);

    await page.goto("/reports/income-vs-expenses");
    await expect(page).toHaveURL(/\/login/);

    await page.goto("/reports/monthly-trends");
    await expect(page).toHaveURL(/\/login/);

    await page.goto("/reports/net-worth");
    await expect(page).toHaveURL(/\/login/);
  });
});
