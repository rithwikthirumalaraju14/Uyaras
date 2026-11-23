const { test, expect } = require("@playwright/test");

test("mobile shopping, account creation, cart merge and COD checkout", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Your everyday. Better dressed." }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "tmp/browser/home-mobile.png",
    fullPage: true,
  });
  await page.goto("/products/boxy-pocket-tee");
  await page.getByRole("button", { name: "Add to bag", exact: true }).click();
  await expect(page.locator("#bag-count")).toHaveText("1");
  await page.getByRole("link", { name: "Bag 1" }).click();
  await page.getByRole("link", { name: "Continue to checkout" }).click();
  await page.locator("#register").getByLabel("Your name").fill("Browser QA");
  await page
    .locator("#register")
    .getByLabel("Email", { exact: true })
    .fill(`qa-${Date.now()}@example.test`);
  await page
    .locator("#register")
    .getByLabel("Password (at least 12 characters)")
    .fill("test-browser-password-2026");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/checkout$/);
  await page.getByLabel("Recipient name").fill("Test shopper");
  await page.getByLabel("Phone", { exact: true }).fill("9999999999");
  await page.getByLabel("Street address").fill("Sample test lane");
  await page.getByLabel("City", { exact: true }).fill("Hyderabad");
  await page.getByLabel("State", { exact: true }).fill("Telangana");
  await page.getByLabel("Six-digit PIN").fill("500001");
  await page.getByRole("button", { name: "Save address" }).click();
  await expect(
    page.getByLabel("Delivery address").locator("option"),
  ).toHaveCount(1);
  await page.getByRole("button", { name: "Review order total" }).click();
  await expect(
    page.getByRole("button", { name: "Place COD order" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "tmp/browser/checkout-mobile.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Place COD order" }).click();
  await expect(page).toHaveURL(/\/orders\/ORD-/);
  await expect(
    page.getByText("Payment: COD due", { exact: false }),
  ).toBeVisible();
  await expect(page.locator(".badge")).toHaveText("Confirmed");
  await page.reload();
  await expect(page.locator(".badge")).toHaveText("Confirmed");
  expect(errors).toEqual([]);
});

test("desktop catalog filters and image gallery", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");
  await expect(page.locator(".product-card")).toHaveCount(4);
  await page.screenshot({
    path: "tmp/browser/home-desktop.png",
    fullPage: true,
  });
  await page.goto("/shop?category=women&size=M&sort=price-asc");
  await expect(page.locator(".product-card")).toHaveCount(2);
  await expect(page.getByLabel("Category", { exact: true })).toHaveValue(
    "women",
  );
  await page.locator(".product-card a").first().click();
  await expect(page.locator(".thumbs button")).toHaveCount(2);
  await page.locator(".thumbs button").nth(1).click();
  await expect(page.locator("#product-image")).toHaveAttribute("src", /moss/);
  await page.screenshot({
    path: "tmp/browser/product-desktop.png",
    fullPage: true,
  });
});

test("owner can edit a draft and audit an inventory adjustment", async ({
  page,
}) => {
  const { execFileSync } = require("node:child_process");
  const { randomUUID } = require("node:crypto");
  const ownerEmail = `qa-owner-${randomUUID()}@example.test`,
    ownerPassword = randomUUID();
  const python =
    process.platform === "win32"
      ? ".venv/Scripts/python.exe"
      : ".venv/bin/python";
  const env = {
    ...process.env,
    QA_OWNER_EMAIL: ownerEmail,
    QA_OWNER_PASSWORD: ownerPassword,
  };
  execFileSync(
    python,
    [
      "-c",
      "import os; from app.store import Store; Store().owner(os.environ['QA_OWNER_EMAIL'],os.environ['QA_OWNER_PASSWORD'])",
    ],
    { env },
  );
  try {
    await page.goto("/account");
    await page
      .locator("#login")
      .getByLabel("Email", { exact: true })
      .fill(ownerEmail);
    await page
      .locator("#login")
      .getByLabel("Password", { exact: true })
      .fill(ownerPassword);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await page.getByRole("link", { name: "Open staff workspace" }).click();
    await page.getByRole("button", { name: "Products", exact: true }).click();
    await page
      .getByRole("button", { name: "New product", exact: true })
      .click();
    const suffix = Date.now();
    await page
      .getByLabel("Product name", { exact: true })
      .fill("QA draft " + suffix);
    await page
      .getByLabel("URL slug", { exact: true })
      .fill("qa-draft-" + suffix);
    await page
      .getByLabel("Variants (JSON; existing SKUs must be retained)")
      .fill(
        JSON.stringify([
          { sku: "QA-" + suffix, colour: "Black", size: "M", active: true },
        ]),
      );
    await page
      .getByRole("button", { name: "Save changes", exact: true })
      .click();
    await expect(
      page.getByRole("cell", { name: "QA draft " + suffix, exact: true }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Stock", exact: true }).click();
    await page
      .getByRole("combobox", { name: "SKU", exact: true })
      .selectOption("QA-" + suffix);
    await page.getByLabel("Quantity adjustment (+ / −)").fill("2");
    await page
      .getByLabel("Reason", { exact: true })
      .fill("Browser QA receiving");
    await page
      .getByRole("button", { name: "Save changes", exact: true })
      .click();
    await expect(
      page
        .locator("tr")
        .filter({
          has: page.getByRole("cell", { name: "QA-" + suffix, exact: true }),
        }),
    ).toContainText("2");
    await page.getByRole("button", { name: "Audit", exact: true }).click();
    await expect(
      page.getByRole("cell", { name: "stock_updated", exact: true }).first(),
    ).toBeVisible();
    await page.screenshot({
      path: "tmp/browser/admin-desktop.png",
      fullPage: true,
    });
  } finally {
    // Only remove the temporary QA owner's identity and sessions, never user data.
    execFileSync(
      python,
      [
        "-c",
        "import os; from sqlalchemy import select,delete; from app.store import Store,users,sessions; s=Store();\nwith s.transaction() as (c,state):\n u=c.execute(select(users).where(users.c.email==os.environ['QA_OWNER_EMAIL'])).mappings().one(); c.execute(delete(sessions).where(sessions.c.user_id==u['id'])); c.execute(delete(users).where(users.c.id==u['id']))",
      ],
      { env },
    );
  }
});
