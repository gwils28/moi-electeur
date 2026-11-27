import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "@playwright/test";

const REAL = "fr-presidentielle-2022";
const dir = join(import.meta.dirname, "..", "public", "data", REAL);
const published = existsSync(join(dir, "positions.json"));
const config = published
  ? (JSON.parse(readFileSync(join(dir, "election_config.json"), "utf-8")) as {
      candidates: unknown[];
      themes: unknown[];
    })
  : { candidates: [], themes: [] };

test.describe("sélecteur d'élection (D33)", () => {
  test.skip(!published, "boussole 2022 non publiée (revue en cours)");

  test("accueil : passage à 2022, mention d'élection passée, questionnaire", async ({ page }) => {
    await page.goto("/");
    const select = page.getByLabel("Élection");
    await expect(select).toHaveValue("demo-fictive");
    await select.selectOption(REAL);
    await expect(page.getByText(/Élection passée/)).toBeVisible();
    await expect(page.getByText(/Élection fictive/)).toHaveCount(0);
    await page.getByRole("button", { name: "Commencer le questionnaire" }).click();
    await expect(page.locator("fieldset").first()).toBeVisible();
  });

  test("comparateur : radar de tous les candidats de 2022", async ({ page }) => {
    await page.goto("/comparateur");
    await page.getByLabel("Élection").selectOption(REAL);
    const radar = page.getByTestId("radar");
    await expect(radar.locator("thead th")).toHaveCount(config.candidates.length + 1);
    await expect(radar.locator("tbody tr")).toHaveCount(config.themes.length);
  });
});
