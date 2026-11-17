import { expect, test } from "@playwright/test";

test("la page d'accueil s'affiche sans requête vers un tiers", async ({ page, baseURL }) => {
  const external: string[] = [];
  page.on("request", (req) => {
    if (!req.url().startsWith(baseURL ?? "http://localhost:3000")) external.push(req.url());
  });
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Moi Électeur");
  expect(external).toEqual([]);
});
