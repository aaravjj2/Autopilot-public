import { test, expect } from "@playwright/test";

test("arb radar shows intelligence verdict badge", async ({ page }) => {
  await page.route("**/api/arb/opportunities?limit=200", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "arb-1",
          kalshi_ticker: "CPI-TEST",
          poly_market_id: "poly-1",
          question: "Will CPI print above 3.0?",
          kalshi_title: "CPI print",
          poly_title: "CPI above 3.0",
          kalshi_yes_ask: 0.48,
          poly_no_ask: 0.49,
          gross_spread: 0.03,
          net_edge: 0.051,
          settlement_match_score: 0.88,
          settlement_flags: [],
          volume_kalshi: 10000,
          volume_poly: 15000,
          category: "macro",
          kelly_fraction: 0.08,
        },
      ]),
    });
  });

  await page.route("**/api/intelligence/report/CPI-TEST", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        verdict: "BUY",
        confidence_score: 84,
      }),
    });
  });

  await page.goto("/dashboard/arb-radar");
  await expect(page.getByTestId("intelligence-verdict")).toContainText("BUY 84%");
});
