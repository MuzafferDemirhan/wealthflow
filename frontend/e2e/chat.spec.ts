import { test, expect } from "@playwright/test";

test.describe("Chat (AI Advisor)", () => {
  test("redirects to login when accessing chat unauthenticated", async ({ page }) => {
    await page.goto("/chat");
    await expect(page).toHaveURL(/\/login/);
  });
});
