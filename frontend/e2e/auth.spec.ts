import { test, expect } from "@playwright/test";

test.describe("Authentication", () => {
  test("landing page shows sign in and create account links", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("WealthFlow")).toBeVisible();
    await expect(page.getByRole("link", { name: /sign in/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /create account/i })).toBeVisible();
  });

  test("login page renders form", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByLabel("Password")).toBeVisible();
    await expect(page.getByRole("button", { name: /sign in/i })).toBeVisible();
  });

  test("register page renders form", async ({ page }) => {
    await page.goto("/register");
    await expect(page.getByLabel("Full Name")).toBeVisible();
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByLabel("^Password$")).toBeVisible();
    await expect(page.getByLabel("Confirm Password")).toBeVisible();
    await expect(page.getByRole("button", { name: /create account/i })).toBeVisible();
  });

  test("login with invalid data shows error", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email").fill("test@test.com");
    await page.getByLabel("Password").fill("wrong");
    await page.getByRole("button", { name: /sign in/i }).click();
    // Should show error (either validation or API error)
    await expect(page.getByText("Login failed")).toBeVisible({ timeout: 10000 });
  });

  test("navigates to register from login", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("link", { name: /create one/i }).click();
    await expect(page).toHaveURL("/register");
  });

  test("navigates to login from register", async ({ page }) => {
    await page.goto("/register");
    await page.getByRole("link", { name: /sign in/i }).click();
    await expect(page).toHaveURL("/login");
  });
});
