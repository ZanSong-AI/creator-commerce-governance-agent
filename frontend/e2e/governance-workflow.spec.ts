import { expect, test } from "@playwright/test";

test("shows review boundaries and all workflow surfaces", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Governance work that can be traced" })).toBeVisible();
  await expect(page.getByText("Evidence and candidates, never legal conclusions")).toBeVisible();
  await expect(page.getByText("50", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Sources", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Source registry" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Sync registry metadata" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Open official source" })).toHaveCount(9);
  await expect(page.getByText(/Latest immutable snapshot/).first()).toBeVisible();

  await page.getByRole("button", { name: "Requirements", exact: true }).click();
  const approveButtons = page.getByRole("button", { name: "Approve candidate" });
  await expect(approveButtons.first()).toBeVisible();
  const requirementCandidates = await approveButtons.count();
  expect(requirementCandidates).toBeGreaterThanOrEqual(5);
  await expect(page.getByText("Approval authorizes mapping work—not a legal conclusion.")).toBeVisible();

  await page.getByRole("button", { name: "Controls", exact: true }).click();
  await expect(page.getByText("No approved requirement exists yet.")).toBeVisible();

  await page.getByRole("button", { name: "Media Cases", exact: true }).click();
  await expect(page.locator(".case-button")).toHaveCount(50);
  await page.locator(".case-button").first().click();
  await expect(page.getByRole("heading", { name: "Evidence bundle" })).toBeVisible();

  await page.getByRole("button", { name: "Audit Pack", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Audit package" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Generate all formats" })).toBeDisabled();
});

test("mobile layout has no horizontal overflow", async ({ page }, testInfo) => {
  test.skip(!testInfo.project.name.startsWith("mobile"), "mobile project only");
  await page.goto("/");
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(overflow).toBe(false);
  await expect(page.getByRole("navigation", { name: "Primary navigation" })).toBeVisible();
});
