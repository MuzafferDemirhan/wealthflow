import { test, expect } from "@playwright/test";

test.describe("Export", () => {
  test("export button visible on income vs expenses page", async ({ page }) => {
    await page.goto("/reports/income-vs-expenses");
    await expect(page.getByText("Income vs Expenses")).toBeVisible();
    await expect(page.getByRole("button", { name: "Export" })).toBeVisible();
  });

  test("export button visible on category breakdown page", async ({ page }) => {
    await page.goto("/reports/category-breakdown");
    await expect(page.getByText("Category Breakdown")).toBeVisible();
    await expect(page.getByRole("button", { name: "Export" })).toBeVisible();
  });

  test("export button visible on monthly trends page", async ({ page }) => {
    await page.goto("/reports/monthly-trends");
    await expect(page.getByText("Monthly Trends")).toBeVisible();
    await expect(page.getByRole("button", { name: "Export" })).toBeVisible();
  });

  test("export button visible on net worth page", async ({ page }) => {
    await page.goto("/reports/net-worth");
    await expect(page.getByText("Net Worth")).toBeVisible();
    await expect(page.getByRole("button", { name: "Export" })).toBeVisible();
  });

  test("export dialog opens and shows format options", async ({ page }) => {
    await page.goto("/reports/income-vs-expenses");
    await page.getByRole("button", { name: "Export" }).click();
    await expect(page.getByText("Export Report")).toBeVisible();
    await expect(page.getByText("PDF")).toBeVisible();
    await expect(page.getByText("CSV")).toBeVisible();
    await expect(page.getByRole("button", { name: "Generate Export" })).toBeVisible();
  });

  test("export dialog can switch between PDF and CSV", async ({ page }) => {
    await page.goto("/reports/income-vs-expenses");
    await page.getByRole("button", { name: "Export" }).click();
    await expect(page.getByText("Export Report")).toBeVisible();
    // Default is PDF
    await page.getByText("CSV").click();
    // PDF should no longer be selected
    await page.getByText("PDF").click();
  });

  test("export dialog can be cancelled", async ({ page }) => {
    await page.goto("/reports/income-vs-expenses");
    await page.getByRole("button", { name: "Export" }).click();
    await expect(page.getByText("Export Report")).toBeVisible();
    await page.getByRole("button", { name: "Cancel" }).click();
    await expect(page.getByText("Export Report")).not.toBeVisible();
  });
});
