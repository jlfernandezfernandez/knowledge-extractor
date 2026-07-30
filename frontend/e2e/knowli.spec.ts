import { expect, test } from "@playwright/test";

test("a contributor can save knowledge and inspect its evidence", async ({ page }) => {
  const email = `e2e-${Date.now()}@example.test`;

  await page.goto("/register");
  await page.getByLabel("Name").fill("E2E Contributor");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("a-safe-password");
  await page.getByRole("button", { name: "Create account" }).click();

  await page.getByLabel("Your contribution").fill("Deploy production on Tuesdays.");
  await page.getByRole("button", { name: "Create contribution" }).click();
  await expect(page.getByRole("heading", { name: "Review claims" })).toBeVisible();

  await page.getByRole("button", { name: "Continue to conflicts" }).click();
  await expect(page.getByRole("heading", { name: "Resolve conflicts" })).toBeVisible();
  await page.getByRole("button", { name: "Continue to save" }).click();
  await expect(page.getByRole("heading", { name: "Ready to save" })).toBeVisible();
  await page.getByRole("button", { name: "Save contribution" }).click();
  await expect(page.getByRole("heading", { name: "Saved" })).toBeVisible();

  await page.getByRole("link", { name: "Ask" }).click();
  await page.getByLabel("Question").fill("When do we deploy?");
  await page.getByRole("button", { name: "Ask" }).click();
  await expect(page.getByRole("heading", { name: "Citations" })).toBeVisible();
  await page.getByRole("button", { name: "Deployment policy" }).first().click();
  await expect(page.getByText("Deploy production on Tuesdays.", { exact: true })).toBeVisible();

  await page.getByRole("link", { name: "History" }).click();
  await expect(page.getByRole("heading", { name: "History" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Review contribution" }).first()).toBeVisible();
});
